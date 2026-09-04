Move the files to a storage service and keep a reference in your database. For a team of four at 200 GB, shared disk is the more expensive option in both money and attention, and it keeps the failure mode you are trying to escape.

What breaks with three machines is worth naming precisely, because it shapes the migration. A file written to machine A's disk does not exist on B or C. Uploads will appear to succeed and then return 404 for roughly two thirds of subsequent requests, depending on which machine the load balancer picks. It is intermittent rather than total, so it will read as flakiness rather than as a clear outage, and it will be reported by users before it is caught by monitoring. Sticky sessions look like a fix and are not one: they only narrow the window until a deploy, a restart, or a scale-in moves the user to a different machine, and by then the file is stranded on a host you may have already terminated.

Shared disk does solve the correctness problem. The cost is that you have introduced a component that all three machines now depend on, and it is a component your team has to keep alive. If you run the NFS server yourself, it is a single point of failure with worse availability than any one of the three app machines, and it needs its own backups, its own capacity planning, and someone who knows how to recover it at 3am. If you buy a managed network filesystem instead, you avoid the operational work but pay heavily for storage you are not doing anything demanding with.

| Option | ~Monthly cost at 200 GB | Egress | Ops burden |
|---|---|---|---|
| Self-run NFS server | Instance + volume, roughly $30–50 | Internal | You own uptime, backups, recovery |
| Managed network FS (e.g. EFS Standard) | ~$60 at $0.30/GB | Internal | Low |
| S3 Standard | ~$5 at $0.023/GB | $0.09/GB after 100 GB free | Provider's |
| Cloudflare R2 | ~$3 at $0.015/GB | $0 | Provider's |
| Backblaze B2 | ~$1.20 at $0.006/GB | Free up to 3× stored/month | Provider's |

Treat those figures as current list prices rather than quotes, and check them against your region before you commit. The storage line is small either way at your size; the number that will actually decide your bill is egress, because photos get served repeatedly. If you are serving a few hundred gigabytes a month of images, AWS bandwidth at $0.09/GB will cost several times your storage, while R2 and B2 charge nothing or nearly nothing for it. Growth of 10 GB a month is noise in all of these: three years out you are at roughly 560 GB, which changes the storage line by a few dollars and changes nothing structurally.

In the application, three things change. Uploads write to the bucket under a key your server generates rather than to a path derived from the user's filename, which also closes off path traversal and accidental overwrites; a UUID or a hash plus the original extension is enough. The database row becomes the source of truth and stores the key, not a full URL, so that switching providers or moving between buckets is a config change rather than a data migration. Serving goes through an endpoint that checks authorization and then redirects to a presigned URL with a short expiry, typically a few minutes, which keeps the bucket private while keeping the bytes off your app servers. For documents you will want `Content-Disposition` set on that presigned URL so downloads arrive with a sensible filename instead of a UUID.

A migration that does not require downtime runs in this order:

1. Add the storage client and the key column, deploy with the code still reading and writing local disk. This is a no-op release that de-risks the ones after it.
2. Switch writes to dual-write: every new upload goes to the bucket and to local disk, and the key is recorded. Reads still come from disk.
3. Backfill the existing 200 GB with a script that walks the table, uploads each file, and records the key. Make it resumable and idempotent so you can stop and restart it, and run it while the site is up.
4. Switch reads to prefer the bucket and fall back to local disk when the key is null. Watch the fallback rate; when it reaches zero, the backfill is genuinely complete.
5. Drop the local writes, then add the third machine.
6. Leave the local files in place for a couple of weeks as a rollback path before deleting them.

Only after step 5 do you add the extra machines, because until then the local-disk fallback in step 4 is still machine-specific.

Two smaller things to decide while you are in there. Deletes are the one place the two stores can drift, since a failed bucket delete after a successful row delete leaves an orphan that nothing points to and nothing cleans up; the usual fix is to mark rows deleted and let a periodic job reconcile, or to enable lifecycle expiry on the bucket. And local disk does not disappear entirely: image resizing, virus scanning, and anything that shells out to a tool expecting a file path still needs scratch space. That is fine, as long as those files are temporary and no request ever depends on one surviving.

The case for shared disk is narrow enough to check quickly and then set aside. It wins if you are on-premises with no object storage available, or if some library in your stack genuinely requires a POSIX path to durable storage and cannot be adapted to read from a stream. Neither is common, and neither is likely to outweigh the ongoing cost of owning a filesystem for four people.