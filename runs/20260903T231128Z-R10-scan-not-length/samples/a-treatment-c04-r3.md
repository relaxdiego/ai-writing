Move the files to a storage service and keep a reference in your database.

The shared-disk option is the one that looks like less work, and for a team of four it is the one that will take the most of your attention over the next two years. A shared filesystem is a service you now operate: it needs its own availability, its own capacity planning, its own backups, and it adds a failure mode your application has never had. When an NFS mount goes slow or hangs, the request threads touching it hang with it, so all three machines degrade together instead of one at a time, and you have not really removed the coupling you set out to remove; you have moved it from the local disk to a box that every machine depends on. Object storage inverts that shape. Durability and replication belong to the provider, capacity is not a number you have to pick in advance, and a bad response comes back as an HTTP error you can retry rather than a wedged syscall.

Price is not an argument for the disk either, and at your volume it is close to noise. Approximate list prices, ignoring request charges:

| Option | Per GB-month | 200 GB today | ~440 GB in two years |
|---|---|---|---|
| Amazon EFS (shared disk) | $0.30 | ~$60/mo | ~$132/mo |
| S3 Standard | $0.023 | ~$4.60/mo | ~$10/mo |
| Cloudflare R2 | $0.015 | ~$3/mo | ~$6.60/mo |
| Backblaze B2 | $0.006 | ~$1.20/mo | ~$2.64/mo |

Your 10 GB a month adds about twenty cents a month to an S3 bill. The line item that can actually surprise you is egress rather than storage, so if these are user photos being served to browsers at any volume, look at R2 or B2, which charge nothing for it, or put a CDN in front of S3.

On the claim that three machines will break it, the mechanism is worth knowing precisely: a photo uploaded through machine A is a 404 when the load balancer routes the next request to machine B. Sticky sessions will hide most instances of this and make the rest look intermittent and unreproducible, so do not reach for them as a stopgap. It is also worth checking whether your disk is already ephemeral. If you deploy in containers or on a PaaS, files may be disappearing on every release already, and nobody has reported it because uploaded documents are rarely re-read soon after they are written.

The migration runs in five steps, none of which needs downtime:

1. Add columns for the storage key, byte size, content type, and a checksum. Store the key and bucket, not a full URL, because URLs change and bake the provider into your data.
2. Send new uploads to the storage service, leaving reads to fall back to disk whenever the key is null.
3. Backfill the existing 200 GB with a resumable script that copies each file and stamps its row. At this size it is a few hours of transfer, and it can be restarted safely as long as the copy is idempotent.
4. Flip reads to the storage service, keeping the disk fallback in place for one release so a missed row is a slow path rather than an error.
5. Delete the disk copies once the fallback has gone unused, retaining a snapshot for a while longer.

Four details are easy to get wrong. Keep the bucket private and serve files through short-lived presigned URLs rather than making it public and relying on unguessable filenames, since those names leak through referrers, logs, and support tickets. Deletion becomes two-phase, because you cannot roll back a delete against the storage service: mark the row deleted inside your transaction and let an asynchronous sweeper remove the object afterwards. Have the browser upload large documents directly with a presigned PUT, so a 200 MB file does not tie up an application worker for the duration. And put the whole thing behind one small interface with a filesystem or MinIO implementation, so local development and tests do not need network access or credentials.