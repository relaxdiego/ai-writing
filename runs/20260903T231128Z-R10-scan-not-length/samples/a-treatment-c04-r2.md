Move the files to a storage service and keep only a reference in your database.

The shared-disk option looks like the smaller change, and that is exactly what makes it a trap for a team of four. A shared filesystem is a piece of infrastructure you now own: it has to be provisioned, mounted on every machine at boot, monitored, backed up separately from your database, and kept available, because when it goes away all three of your machines go down together rather than one of them. You have traded a single point of failure you understood for one you have to operate. Managed NFS (EFS, Filestore, Azure Files) removes some of that work but not the mount-and-monitor part, and it introduces latency and locking behaviour that ordinary file code is not written to expect. Object storage, by contrast, is a service you call over HTTP and otherwise do not think about.

It is also worth being precise about what breaks with three machines, because it shapes the migration. A user uploads a photo, the load balancer sends that request to machine A, and the bytes land on A's disk. The next request, for the page that displays the photo, goes to machine B, which returns a 404. Sticky sessions appear to fix this and do not: they only mean the failure waits until the user's next session, or until A is replaced during a deploy. The same applies to any derived files you generate, such as thumbnails or extracted document text.

Cost pushes the same direction, at least at list prices for a US region, which you should confirm against your own provider and region:

| Option | 200 GB today | 560 GB in three years |
|---|---|---|
| S3 Standard | $4.60/mo | $12.88/mo |
| Cloudflare R2 | $2.85/mo | $8.25/mo |
| EFS Standard (shared disk) | $60/mo | $168/mo |

Those figures cover storage only. S3 and its equivalents also bill for requests and for egress, and egress is the line that surprises people if you serve many large files directly to browsers; R2 charges nothing for egress, which is why it is worth a look for a photo-heavy workload. At your growth rate neither option ever hits a capacity wall, so the decision really is about operational burden and not about scale.

The migration is a weekend's work at 200 GB, and it goes in this order:

1. Add a column for the storage key to whatever table already records the file. Keep the existing path column until the end.
2. Write new uploads to both places, disk and bucket, and keep reading from disk. Nothing user-visible changes yet.
3. Backfill the 200 GB with a parallel copy tool (`aws s3 sync`, `rclone`), recording each key as you go. Run it as many times as you like; it is idempotent.
4. Switch reads to the bucket, with a fallback to disk when the key is missing. Watch how often that fallback fires.
5. When it stops firing, stop the dual write, then delete the disk copies and the old column.

One design decision inside that is worth getting right the first time. Do not let your application servers proxy the bytes: issue a short-lived presigned URL and have the browser PUT to and GET from the bucket directly, so your web tier stays out of the data path and your bandwidth bill stays on the storage service. Keep the bucket private, generate object keys as opaque UUIDs rather than from user-supplied filenames, and store the original filename as metadata in your database, where it belongs. The database remains the source of truth for who owns what; the bucket is a dumb store of blobs that only your signed URLs can reach.

There is a case where shared disk is the right answer, and you should check whether you are in it before committing. If some part of your system needs real POSIX semantics, meaning it mmaps files, seeks and writes in place, or hands paths to a third-party binary that will not take a URL, object storage will fight you the whole way. Regulatory or on-premise constraints that keep data off a cloud service have the same effect. Absent one of those, the file is a blob, your access pattern is write-once-read-many, and object storage is what that shape is for.