Move the files to a storage service and keep only a reference in the database.

The reason isn't that shared disk can't work. NFS or EFS behind three app servers is a real deployment, and it's the smaller code change: your upload path keeps writing to a path, and you point that path at a mount. The reason is that it puts a filesystem you now have to operate underneath every request that touches a photo. A stale mount, a slow metadata operation, or a full volume takes all three machines down at once, and the team that has to diagnose that at 2am is four people who presumably have other things to build. Object storage moves that operational surface to someone whose job it is.

The cost difference points the same way, and it's larger than people expect, because network filesystems are priced per gigabyte-month at roughly ten times object storage rates:

| | 200 GB today | ~440 GB in two years | What you still owe |
|---|---|---|---|
| S3-class object storage | ~$5/mo | ~$10/mo | request and egress charges |
| EFS-class shared filesystem | ~$60/mo | ~$130/mo | your own backup and snapshot story |

Egress is the number to watch rather than storage. If these are profile photos rendered on every page load, put a CDN in front of the bucket and let it absorb the repeat reads; that is a bigger lever on the bill than the storage tier.

The part that actually takes work is the write path, and it's worth getting right the first time. An upload becomes two operations that can fail independently: put the bytes in the bucket, then commit the database row that points at them. Do them in that order. If the process dies between the two, you have an orphaned object nobody references, which a lifecycle rule or a weekly sweep can clean up quietly. Do them in the other order and you have a database row pointing at nothing, which is a broken image in a user's face and a support ticket. Store an opaque key rather than a full URL, so that changing bucket, region, or CDN later is a config change instead of a data migration.

Serve downloads with presigned URLs rather than streaming bytes through your application. Proxying works and is tempting because it keeps your existing authorization code in one place, but it ties up an app worker for the length of every download and puts your bandwidth back on your own machines. Generate a short-lived signed URL after you've run the same permission check you run today, and redirect.

For the migration itself, the sequence that avoids a flag day is to write new uploads to both the local disk and the bucket for a period, backfill the existing 200 GB with a bulk copy tool while that's running, switch reads to the bucket once the backfill verifies, and drop the disk writes a week later when you're confident. Two hundred gigabytes copies in hours, not days, so the backfill is not the hard part; the dual-write window is what buys you a cheap rollback.

One case genuinely favors the filesystem: if your code mutates files in place, seeks within them, or hands paths to a library that insists on real files, object storage will fight you. Image processing usually does need a real file, but downloading to a temp file, processing, and uploading the result is a small wrapper and not a reason to change the decision. If you're doing something heavier, like appending to files over their lifetime or serving byte ranges out of large documents, say so, because that would change the analysis.