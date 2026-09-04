Move the files to a storage service and keep only a reference in your database. For a team of four with photos and documents, object storage is the right answer, and shared disk is a trap that looks cheaper than it is.

Here is what actually breaks when you go to three machines. A file uploaded through machine A lands on machine A's disk, and a later request for that file is load-balanced to machine B or C, which cannot see it. So roughly two requests in three fail, and they fail in a confusing way that depends on which machine served the upload and which serves the view. Worth noticing too is that this is already a durability problem on one machine: if that machine is ever replaced, rebuilt, or lost, the files go with it. Whatever backup story you have today, check it before you migrate, because a lot of teams discover at this exact moment that the answer is "none."

The cost difference is not marginal:

| | Object storage (S3/GCS/R2) | Shared network disk (EFS/managed NFS) |
|---|---|---|
| 200 GB today | ~$5/month | ~$60/month |
| ~320 GB in a year | ~$7/month | ~$95/month |
| Serving downloads | egress billed per GB, cheap behind a CDN | included, but bandwidth from the app machines |
| Failure mode | none you operate | a shared mutable dependency all three machines need |
| Operational work | credentials and a bucket policy | mounts, permissions, capacity, latency tuning |

The dollar figures are order-of-magnitude and region-dependent, but the ratio holds: network filesystems bill at roughly ten times the price of object storage per gigabyte, because you are paying for POSIX semantics you do not need. Photos and documents are written once and read whole. You never seek into the middle of a JPEG or take a lock on it.

The operational point matters more than the money at your size. A shared disk is one more piece of infrastructure that four people have to understand, mount correctly on every new machine, monitor for capacity, and reason about when it gets slow. It also reintroduces a single thing that all three machines depend on, which partly undoes the reason you are moving to three machines. Object storage is a bucket, a set of credentials, and an SDK call, and nobody has to be on call for it.

Shared disk is defensible in a narrow case: if your code or a third-party tool you depend on needs a real filesystem path — image processing libraries that only accept paths, virus scanners, document converters — and rewriting that is genuinely hard. Even then the usual fix is to download the object to a temporary local file, run the tool, and upload the result, which is a small wrapper rather than an infrastructure decision. Check whether anything in your codebase does something more exotic with those files than read and write them whole; if nothing does, the case for shared disk is empty.

A migration path that lets you move without a flag day:

1. Put every filesystem call behind one small storage interface — `put`, `get`, `delete`, `url_for` — with the current disk behaviour as the first implementation. Do this while still on one machine and ship it.
2. Add an object-storage implementation of the same interface, and a column on the file record marking where each file lives.
3. Switch new uploads to object storage. Reads check the marker and fall back to disk.
4. Backfill the existing 200 GB with a script that copies and flips the marker. At normal bandwidth this is hours, not days, and it is resumable and re-runnable.
5. When no records point at disk, delete the disk branch and go to three machines.

Two details worth getting right the first time. Have browsers upload directly to storage using a presigned URL your app issues, rather than routing the bytes through your application servers; otherwise a few large uploads can tie up your web workers. And since these are files attached to individual accounts, keep the bucket private and serve downloads through short-lived signed URLs, checking your own authorisation before you issue one. Public-read buckets are how private documents end up indexed by search engines.