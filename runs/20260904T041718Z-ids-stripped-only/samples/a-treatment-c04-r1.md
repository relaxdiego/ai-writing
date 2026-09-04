Move the files to a storage service and keep a reference in the database.

The thing that breaks on three machines is not really the disk, it's the assumption that whichever machine handled the upload will also handle the download. Behind a load balancer that stops being true, so a photo uploaded through machine one comes back as a 404 roughly two times in three. Both options you named fix that. The difference is what you own afterwards. A shared disk fixes it by adding a filesystem server that all three machines mount, and that server is now a piece of infrastructure with its own failover story, its own backup story, its own capacity ceiling and its own ability to take the whole site down when it goes unreachable. Object storage fixes it by removing files from your infrastructure entirely. For a team of four, the second is the one you can afford to operate, and the code change is about a day's work.

The cost gap points the same way, and it is wider than people expect because the two services are priced on different models. Figures below are order-of-magnitude for AWS in a US region and worth re-checking against current pricing, but the ratio is stable across providers:

| | Shared disk (EFS/NFS) | Object storage (S3 et al.) |
|---|---|---|
| 200 GB stored | ~$60/month | ~$5/month |
| Each +10 GB/month adds | ~$3/month | ~$0.25/month |
| You operate | mount targets, capacity, failover, snapshots | nothing |
| Worst failure | share unreachable, site down | request fails, retry |
| Backups | your job (snapshots, tested restores) | versioning flag, one line of config |

Bandwidth to end users costs the same either way and will dominate both columns once traffic is real, so put a CDN in front of whatever you choose.

In the database, store the object key, not a URL. Keys are stable and URLs are not: the moment you add a CDN, change buckets, or move regions, a table full of hardcoded hostnames becomes a migration. Alongside the key, record the bucket or a short storage-location tag, the original filename as the user typed it, the content type, the byte size and a checksum. Serving then works by looking up the row, checking that this user may read this file, and issuing a presigned URL with a short expiry rather than streaming the bytes through your application. Keep the bucket itself private. Presigned URLs are the whole access-control story for private per-account files, and they let the storage service absorb the transfer instead of tying up an application process for the length of a slow download.

Getting there without downtime is four steps:

1. Put a small storage interface in front of every place that currently touches the filesystem, with `put`, `get`, `delete` and `url_for`. This is the only invasive change; do it while still on one machine and still writing to local disk, and confirm the site behaves identically.
2. Switch new writes to object storage and add the key column. New uploads go to the service; old rows still point at local paths, and reads check which kind of reference the row holds.
3. Backfill the 200 GB with a script that walks existing rows, uploads, sets the key, and verifies the checksum before marking the row done. Make it resumable and run it in batches. At this volume it is hours, not days.
4. Once no rows reference local paths, remove the local branch from the read path, then delete the files from disk. Keep the disk copy for a couple of weeks after the code stops reading it.

Only step two onward needs the three machines to be running, so you can do the risky part on your current single-machine setup and treat the scale-out as a separate, boring change.

There is a case where shared disk is the right answer, and it is worth checking whether you are in it before committing. If your code hands file paths to something that insists on a real filesystem, seeks around inside large files, or edits files in place, object storage will fight you. Document previews, thumbnailing and virus scanning are the usual suspects. Most of the time the fix is to download to a temp file, do the work, upload the result, and that is fine at your file sizes. If instead you have a library that memory-maps a 20 GB file, or an on-premise deployment with no object storage available and no appetite for running MinIO or Ceph, the shared disk earns its operational cost. Nothing in what you have described suggests you are in that case.