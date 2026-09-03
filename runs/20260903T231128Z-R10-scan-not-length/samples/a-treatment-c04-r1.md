Move the files to a storage service and keep only a key in your database.

The breakage you were warned about is real and immediate: a user uploads a photo, the load balancer sends their next request to a different machine, and the file is not there. It shows up as intermittent broken images and downloads that work on refresh, which is miserable to debug because it depends on which machine answered. Sticky sessions paper over it until a machine restarts or you deploy, so they are not a fix.

The shared-disk option does solve that, but it makes your team of four the operator of a distributed filesystem. You inherit NFS locking and caching semantics, a mount that can hang every machine at once when it goes unhealthy, permission and UID alignment across hosts, and a backup story you have to build yourself. On managed pricing it is also the expensive choice: EFS-class storage runs roughly ten times object storage per gigabyte at current list prices, so your 200 GB costs around sixty dollars a month rather than around five, and it keeps a single failure domain in the middle of your architecture. Object storage gives you durability, versioning, lifecycle rules, and server-side encryption without any of you learning to run them.

At your size the cost is not a factor worth modelling carefully. 200 GB on S3 standard is under five dollars a month, and at 10 GB a month you are still under fifteen dollars three years from now. The number that can actually surprise you is egress, so if users download their files often, look at Cloudflare R2 or Backblaze B2, where egress is free or nearly so, or put a CDN in front of S3. Both speak the S3 API, so the choice does not change your code.

A migration that does not require downtime looks like this:

1. Add a column for the storage key alongside the existing path column. Store an opaque key, not a URL, so you can change bucket, provider, or domain later without a data migration.
2. Change the upload path to write to object storage and record the key. New files stop landing on disk from that moment.
3. Change the read path to use the key when present and fall back to the local path when it is null.
4. Backfill in the background, copying existing files up and filling in keys. Run it against a copy first so you know the throughput and the failure modes.
5. Once no rows have a null key, delete the fallback branch and the local files.

Two details are worth getting right while you are in there. Write the object first and commit the database row second: if the commit fails you are left with an unreferenced object, which a weekly sweep can clean up, whereas the opposite order leaves a row pointing at nothing and your user sees a 404. And serve downloads with short-lived presigned URLs rather than proxying bytes through your application, which keeps your access-control check in your own code while keeping the file traffic off your web machines entirely.