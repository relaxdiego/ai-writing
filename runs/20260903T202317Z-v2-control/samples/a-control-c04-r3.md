## Recommendation

Move to object storage (S3, Cloudflare R2, GCS, Azure Blob) and keep only a reference in the database. For a team of four with write-once/read-many user uploads, this is the clear default. Shared disk is the option you pick when something forces you into it, and photos and documents don't.

## Why the shared disk is the worse trade

The appeal is real: NFS/EFS/Filestore keeps your code unchanged, since a file path is still a file path. But you're buying that with:

- **A new single point of failure.** You went to three machines for availability. A shared volume puts one thing back in the middle of all three. Making *that* highly available is a second infrastructure project.
- **Ops load you have to carry.** Capacity, snapshots, backup verification, patching, monitoring, and the fun of debugging stale NFS handles and lock contention. That's a real fraction of one engineer out of four, forever.
- **Bytes flow through your app servers.** Every download occupies a request worker and your machines' bandwidth. With object storage you hand out a presigned URL and the client fetches directly from the storage service, or from a CDN in front of it.
- **Cost, roughly 10x.** EFS-class network filesystems run about $0.30/GB/month → ~$60/month at 200 GB. S3 standard is ~$0.023/GB → ~$4.60/month. At your growth rate you're at ~560 GB in three years: ~$13/month vs. ~$170/month. Neither number is scary; the point is that the cheaper option is also the one with less work in it.

Shared disk earns its place when the application genuinely needs POSIX semantics — in-place random writes, hard links, `mmap`, third-party tools that only speak file paths — or when a regulatory constraint keeps data on hardware you control. Uploaded photos and documents are written once and read many times. That's exactly the workload object storage was built for.

## What to store in the database

Store a **key, not a URL**. Building the URL at read time means you can change bucket, provider, or CDN without rewriting rows.

A file row wants roughly: id, owner id, bucket, object key, original filename, content type, byte size, checksum, status, created/deleted timestamps.

Two details that bite people later:

- **Never use the user-supplied filename as the object key.** Generate a UUID/ULID. Keep the original name in a column and set it as `Content-Disposition` on download.
- **Uploads should be two-phase.** Create the row as `pending`, hand the browser a presigned upload URL (with content-length and content-type limits baked into the policy), then mark it `ready` after you confirm the object exists. A small sweeper deletes rows that never got confirmed. Without this you get database rows pointing at objects that don't exist, and orphaned objects nobody knows about.

Also: block all public access on the bucket, serve private files via short-lived presigned GETs, force `Content-Disposition: attachment` and serve user content from a separate domain — an uploaded HTML or SVG file served inline from your main domain is a stored XSS.

## Migration path, with no downtime

1. Add a `storage_backend` column (`disk` | `object`) plus the key columns.
2. Put a small storage interface in the code with two implementations. This is the only invasive change, and it's usually a day's work.
3. **Switch writes first.** New uploads go to object storage. Reads branch on `storage_backend`.
4. **Backfill the 200 GB** with `rclone` or `aws s3 sync` from the current machine, then flip rows to `object` after verifying checksums. 200 GB is a background copy, not an event.
5. Verify counts and checksums, remove the disk read path, and delete the local files after a retention window.
6. **Then** scale to three machines.

If you're under time pressure to scale out sooner, note that sticky sessions won't rescue you here — a file uploaded on machine A must be readable by machine B regardless of routing. Finish step 5 first.

## One thing to check on cost

The storage bill is trivial; egress is where object storage surprises people. S3 charges ~$0.09/GB out. If you serve a lot of photo traffic, either put a CDN in front (cheaper egress, better latency) or use Cloudflare R2, which has no egress fees. Worth five minutes of estimating your monthly served-bytes before you pick a provider.

## While you're at it

"Running on three machines will break" is usually true of more than files. Before you cut over, check whether anything else assumes one box: sessions stored on local disk, cron jobs that would now fire three times, in-process caches or rate limiters that will each hold a third of the truth, and log files written locally with no shipper. These are all smaller fixes than the file one, but they fail in more confusing ways.