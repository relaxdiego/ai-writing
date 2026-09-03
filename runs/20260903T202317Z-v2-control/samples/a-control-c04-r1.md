## Recommendation: move to object storage, keep a reference in the database

For a team of four with 200 GB growing at 10 GB/month, this isn't close. Object storage (S3, GCS, Azure Blob, R2, Spaces) is the right call, and the shared-disk option mostly moves the problem rather than solving it.

**Why not shared disk**

A shared filesystem across three machines means either a managed NFS product (AWS EFS, Azure Files, Filestore) or something you run yourself. Self-hosting NFS or GlusterFS gives you a new stateful system to patch, monitor, back up, and fail over — with four people, that's a real tax, and a single NFS server just relocates the single point of failure from "the web box" to "the file box."

Managed NFS avoids the ops burden but is expensive for what you get: EFS standard storage runs roughly 10x the per-GB price of S3, so your 200 GB costs on the order of $60/month instead of about $5, and the gap widens as you grow. You also keep the properties that make shared disk awkward: latency on every stat/read, capacity you have to think about, no built-in HTTP serving, and file uploads/downloads still flowing through your application servers.

The deeper issue is that shared disk preserves a design where your app servers are stateful-adjacent. You'd hit the same friction again at the next step — containers, autoscaling, blue/green deploys, a second region, local dev parity.

**What object storage buys you**

Your app servers become genuinely disposable, which is the actual goal of going from one machine to three. Beyond that: durability and replication are someone else's problem, capacity is unbounded, you get lifecycle rules and versioning for free, and — the big one — uploads and downloads can bypass your application entirely via pre-signed URLs. The client PUTs directly to the bucket and GETs directly from it (or through a CDN), so a 50 MB document upload never occupies a request thread on your web tier.

## Shape of the implementation

**Data model.** Store a stable, opaque storage key, not a URL. URLs embed the provider, region, and bucket, all of which change; keys don't.

```
files
  id            uuid pk
  owner_id      fk
  storage_key   text        -- e.g. "u/8f3a.../2026/09/9d2c1e....pdf"
  bucket        text        -- lets you migrate buckets incrementally
  content_type  text
  byte_size     bigint
  checksum      text        -- sha256, for dedupe + integrity
  original_name text        -- what the user called it; never used as a path
  created_at    timestamptz
```

Generate keys yourself from a UUID. Never build a path from a user-supplied filename — that's a path-traversal and collision bug waiting to happen. Keep the original name as a display label only, and set it via `Content-Disposition` on download.

**Access control.** Bucket stays private, no public read. Serving a file means your app checks that this user may see this object, then issues a short-lived pre-signed GET URL (5–15 minutes) and redirects. Uploads work the same way in reverse: the client asks your API for a pre-signed PUT, and you constrain content type and maximum size in the signature. This is the step teams most often skip, and it's how "private" documents end up indexed by search engines.

**Uploads and post-processing.** Since the file lands in the bucket without touching your app, record a `pending` row first, then confirm it — either from a client callback or, more reliably, a bucket event notification. A periodic sweep deletes `pending` rows older than a day whose objects never materialized. Thumbnailing and virus scanning become background jobs triggered by the same event.

## Migration path

You can do this without downtime, and the ordering matters because you're changing where the bytes live while the site keeps serving:

1. Add the new columns and a storage abstraction with two backends (disk, object store). Ship it with disk still active — no behavior change.
2. Flip **writes** to object storage. New uploads go to the bucket; old files still read from disk. Reads consult the `storage_key` column: null means legacy disk.
3. Backfill the 200 GB in the background with a script that copies, verifies the checksum, then sets `storage_key`. Resumable, restartable, rate-limited. This is the long-running step; at 200 GB it's hours, not days.
4. Once no rows lack a `storage_key`, delete the read-from-disk branch and the local files.

Do steps 2–4 *before* you scale to three machines if you can. Otherwise a file uploaded to machine A is invisible from machines B and C during the window — which is exactly the breakage you were warned about.

If you must scale out first, the stopgap is sticky sessions plus rsync between boxes, and it's genuinely bad: it's eventually-consistent in a way users will notice as "my photo disappeared and came back." Prefer to sequence the migration first.

## Things worth deciding now

**Provider.** If you're already on AWS/GCP/Azure, use theirs — the IAM integration is worth more than a price difference measured in single-digit dollars. If you're on bare metal or expect heavy download traffic, Cloudflare R2 or Backblaze B2 are S3-API-compatible with no egress fees, which matters if users download a lot. Egress, not storage, is what surprises people on the bill: 200 GB at rest is about $5/month on S3, but 2 TB/month of downloads is roughly $180 in transfer. Put a CDN in front regardless.

**Local development.** Run MinIO in Docker (S3-compatible) so dev and prod use the same code path. Don't keep a filesystem backend "just for dev" — the two paths drift and you get bugs that only appear in production.

**Backups.** Object storage is durable, not backed-up: it will faithfully replicate your accidental `DELETE`. Turn on versioning plus a lifecycle rule that expires old versions after 30–90 days, and either cross-region replication or a scheduled sync to a second account. Your files and your database are now separate systems that can get out of sync, so make sure your restore procedure covers both together — a database restored to Tuesday referencing objects deleted on Wednesday is its own kind of outage.

**One caveat on the recommendation:** if your access pattern involves POSIX semantics — random seeks into large files, in-place appends, a tool that only reads local paths — object storage will fight you, and a shared filesystem is the honest answer. For user-uploaded photos and documents that are written once and read whole, that doesn't apply.