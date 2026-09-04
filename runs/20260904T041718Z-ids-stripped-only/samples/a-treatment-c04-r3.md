Move the files to a storage service and keep a reference in your database. At your size and team size, the shared disk is the option that costs more and asks more of you, and it does not actually remove the thing that is about to break.

Worth naming what breaks first, because it shapes the migration. With three machines behind a load balancer, an upload that lands on machine A is invisible to B and C, so a user uploads a photo and then gets a 404 on it two seconds later, depending on which machine answers. Sticky sessions will appear to fix this in testing and will keep failing in production, since any deploy, restart, or scale-down strands whatever was on that machine's disk. Treat local disk as scratch space that can vanish, and the problem becomes tractable.

The comparison at 200 GB growing 10 GB a month:

| | Shared disk (NFS/EFS) | Object storage (S3/R2/GCS) |
|---|---|---|
| Storage cost, 200 GB | ~$60/month at EFS rates | ~$5/month at S3 rates, less on R2/B2 |
| Serving traffic | Through your three app servers | Direct to the client, app servers untouched |
| Durability and backup | You configure and verify it | Built in, versioning is a config flag |
| Failure mode | One filesystem all three machines need | Independent of your machines |
| Work for a team of four | Mount points, permissions, locking, capacity planning | An SDK call and a bucket policy |

The cost column is the smaller argument. The real one is the last row: a shared filesystem is a piece of infrastructure that four people now have to own, monitor, back up, and grow, and it reintroduces a single dependency shared by every machine. Object storage is a bucket and a credential.

One caveat on cost that catches people out. If you serve a lot of photos, egress can exceed storage: S3 charges roughly $0.09/GB out, so a busy image workload can bill more for delivery than for the 200 GB sitting there. Cloudflare R2 and Backblaze B2 charge nothing for egress and speak the S3 API, so if the files are user-facing images being viewed often, start there and keep your code portable.

For the migration itself:

1. Add a column for an opaque storage key, not a URL. Store `users/1234/abc-def.jpg`, not `https://bucket.s3.../abc-def.jpg`, so you can change bucket, region, or provider later without rewriting rows.
2. Write new uploads to both local disk and the bucket, reading from disk. This is a no-risk deploy: nothing changes for users.
3. Backfill the existing 200 GB with a script that walks the current files, uploads each one, and fills in the key. At that volume it is an afternoon, and it is restartable if you make it skip rows that already have a key.
4. Flip reads to the bucket. Keep the disk files for a couple of weeks as your rollback.
5. Delete the disk copies and remove the dual-write.

Three details that are easier to get right now than to retrofit. Keep the bucket private and serve through short-lived presigned URLs, since a public bucket means anyone with a guessed key reads another customer's documents; your app checks authorization, then mints a URL good for a few minutes. Have the browser upload directly to the bucket with a presigned PUT rather than streaming through your app servers, which keeps large uploads from occupying a request worker. And accept that the database and the bucket can disagree: write the object first and the row second, so a crash leaves an orphaned object rather than a row pointing at nothing, and clean up orphans with a periodic job instead of trying to make the two writes atomic.

The one case that would change this answer is a regulatory constraint requiring the files to stay on hardware you control. If that applies, run MinIO or Ceph on your own machines and keep the same S3 API and the same application code, rather than falling back to a shared filesystem.