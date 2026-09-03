## Move to object storage. It isn't close.

First, to confirm what you were told: yes, this breaks, and it breaks in an ugly way. Once three machines sit behind a load balancer, a user's upload lands on the disk of whichever machine handled the POST. Their next request — the one that displays the photo — is routed to a different machine, which has no such file. You get intermittent broken images and 404s that depend on load-balancer routing, so they'll be maddening to reproduce. It won't fail cleanly at deploy time; it'll fail for a third of requests, unpredictably.

## Why not the shared disk

A shared filesystem (NFS, EFS, a SAN) is the smaller-looking change, which is exactly its appeal. But for a team of four it's the worse trade:

- **You've replaced one single point of failure with a scarier one.** If the share is unavailable or slow, *all three* machines stall — often in a way that hangs request threads rather than erroring fast. Local-disk failure at least only takes down one machine.
- **It's the most expensive storage tier by a wide margin.** AWS EFS runs roughly $0.30/GB/month; S3 Standard is about $0.023/GB/month. On 200GB that's roughly $60/month versus roughly $5. Both are small, but you're paying 13× for the option that also costs you more operational attention.
- **Someone has to own it.** Mount options, `nolock` vs. locking semantics, stale file handles after a reboot, growing the volume, snapshotting it, testing that the snapshots restore. That's a part-time infrastructure job spread across four people who presumably have product work to do.
- **It doesn't get you anything later.** You still can't easily put a CDN in front, still hand-roll lifecycle rules, still can't cheaply serve files without going through your app servers.

The one case where shared disk genuinely wins is if you have a hard requirement that data never leave your own hardware, and even then I'd reach for self-hosted object storage (MinIO, Ceph) over a raw filesystem.

## What "reference in the database" should actually mean

The important detail is *what* you store, and it's a place teams commonly go wrong:

**Store an opaque storage key, not a URL.** Something like `uploads/2026/09/{uuid}`. If you store `https://my-bucket.s3.amazonaws.com/...` in the database, you have baked your provider, region, and bucket name into a million rows, and changing any of them becomes a migration. Store the key; construct the URL at read time.

**Derive the key from a UUID, never from the user's filename.** Keep the original filename as a separate display column. User-supplied names bring path traversal, unicode normalization surprises, and collisions when two people upload `scan.pdf`.

A reasonable row: `id`, `owner_id`, `storage_key`, `original_filename`, `content_type`, `size_bytes`, `checksum`, `created_at`.

**Keep the bucket private and serve through short-lived presigned GET URLs** (minutes, not days), generated only after your app has checked that this user may see this file. A public bucket means the ability to guess or leak one URL is permanent, unauthenticated access. For uploads, start by proxying through your app — it's simpler and lets you validate — and switch to presigned PUT later if large files start tying up request workers.

**On provider:** for photo-heavy serving, egress fees dominate storage fees. S3 charges about $0.09/GB out. Cloudflare R2 and Backblaze B2 have zero or near-zero egress and S3-compatible APIs, which for a small team serving user images is often the better economics. Whichever you pick, use the S3-compatible API through a library that lets you swap the endpoint.

## Migrating

200GB is genuinely small — this is a weekend of work, not a quarter. And it only ever gets bigger, so doing it before the three-machine cutover is the cheap moment.

1. Add the metadata table/columns alongside the existing path field.
2. **Dual-write:** new uploads go to object storage *and* record the key. Reads check for a storage key first, fall back to local disk.
3. **Backfill** existing files with a resumable script, verifying checksums as you go.
4. Verify every row has a key and every key resolves.
5. Drop the fallback path and the local files.

You can run steps 1–3 on the current single machine, then add machines once the fallback path is gone.

## Things that will bite you

- **The database and the blob store are not transactional together.** Write the object first, then the row; a failed row insert leaves an orphaned object, which is harmless. The reverse leaves a row pointing at nothing, which is a user-visible error. On delete, delete the row first and sweep objects asynchronously.
- **You'll accumulate orphans anyway.** Plan a periodic reconciliation job from day one; it's much harder to write once you have millions of objects and no idea which are live.
- **Don't trust the client's `Content-Type`.** Sniff it server-side, and serve with an explicit correct type plus `Content-Disposition: attachment` for anything you don't intend to render inline — otherwise an uploaded HTML or SVG file becomes stored XSS against your own domain.
- **Photos carry EXIF GPS data.** If images are shown to other users, strip it on ingest.
- **Set a size cap and enforce it during streaming**, not after the whole body is buffered.

Happy to sketch the upload handler and the backfill script if you tell me your stack.