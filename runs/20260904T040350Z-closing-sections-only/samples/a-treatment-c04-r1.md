Move the files to a storage service and keep only a reference in your database.

The thing you've been told will break is precise and worth naming: a user uploads a photo, the load balancer sends that request to machine A, the file lands on A's disk, and the next request for that file goes to machine B, which returns a 404. The common first fix is sticky sessions, which appears to work and then fails the moment a machine restarts or a user comes back tomorrow on a new connection. So you do need to do something, and your two options are the ones you named.

A shared disk does fix it. The cost is that you now operate a filesystem. If it's a managed one (EFS on AWS, Azure Files, Filestore on GCP) you're paying roughly ten times per gigabyte for storage that behaves like a disk, and small-file reads over NFS are noticeably slower than local ones, which matters if you serve thumbnails. If it's a filesystem you run yourself, you've built a single machine that all three application servers depend on, and now it needs monitoring, capacity planning, and a failover story. For a team of four, that's a job nobody has time to hold.

| | 200 GB today | What you operate | If it goes down |
|---|---|---|---|
| Managed network filesystem | ~$60/mo (EFS Standard, $0.30/GB) | Mount points, capacity, IOPS mode | All three machines lose file access at once |
| Object storage | ~$4.60/mo (S3 Standard, $0.023/GB) | Nothing | Provider's problem, and it's replicated across zones |

At 10 GB of growth a month, neither number is going to hurt you for years. The reason to choose object storage isn't the storage bill.

The one number that can surprise you is egress. S3 charges about $0.09/GB to send data out, so if you're serving a lot of photos to browsers, bandwidth will cost more than storage. Cloudflare R2 charges no egress at all and about $0.015/GB to store, and Backblaze B2 is similar; both speak the S3 API, so your code doesn't care which you pick. If you're already on AWS and want to stay there, put CloudFront in front of the bucket. If you have no strong tie to a cloud, R2 is the boring choice for a workload that is mostly reads of user photos.

What changes in your code is narrower than it looks, but it isn't nothing:

- The upload path stops writing to disk and writes to the bucket, storing the returned key on the record instead of a path.
- The download path stops streaming from disk. Either you issue a short-lived presigned URL and redirect the browser to it, or you proxy the bytes through your app. Presigned URLs are better; they take the traffic off your servers entirely.
- Anything that opens a local path has to change. Image resizing, thumbnail generation, virus scanning, PDF text extraction, building a zip of someone's documents. These become download-to-a-temp-file, do the work, upload the result, delete the temp file. Move them to a background worker if they aren't there already.

Keep the files private. A bucket of user photos and documents that is publicly readable is a bucket whose contents are one guessed URL away from being someone else's, and object keys leak through referrer headers and shared links. Block public access at the bucket level and serve everything through presigned URLs that expire in minutes, checking your own authorization before you sign.

The migration itself can be done without downtime, in this order:

1. Add a storage key column alongside the existing path column. Nothing reads it yet.
2. Start writing new uploads to the bucket, populating the key. Reads check for a key first and fall back to the local path.
3. Copy the 200 GB across with `rclone` or `aws s3 sync`, backfilling keys as you go. This runs for a few hours and is restartable.
4. Once nothing falls back to a path, drop the fallback and the column.

Doing it in that order also means the switch to three machines isn't blocked on the copy finishing.

Two adjacent things will bite you in the same week, from the same cause. Anything else that assumed one machine breaks now too: sessions held in local memory or local files, and any cron job or scheduled task that will start running three times instead of once. Worth auditing before you scale out rather than after.

The honest case for the shared disk is if you're on your own hardware with no object storage available, or if some library you depend on genuinely requires POSIX semantics and can't be worked around. Neither sounds like your situation.