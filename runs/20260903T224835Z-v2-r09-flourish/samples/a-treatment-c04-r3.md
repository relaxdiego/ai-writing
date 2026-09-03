Move the files to a storage service and keep a reference in the database.

The shared-disk option looks cheaper because it changes less application code, but it changes what your team operates. A network filesystem is a distributed system with its own failure modes: stale handles, lock contention, a mount that hangs and takes all three web processes down with it rather than failing fast. Whether it is EFS, a NAS, or an NFS box you run yourself, its availability becomes your site's availability, and it needs monitoring, capacity planning, and a backup story separate from the one you already have for your database. For four people that is a standing tax on attention, paid to avoid a one-time piece of work.

Cost is not what decides this. 200GB on S3-class storage runs about five dollars a month, and at 10GB of growth you are still under ten dollars a month two years from now. What the money buys is that durability, replication, and "does this survive a machine dying" stop being questions you answer.

The work is in your code rather than the data, and it lands in three places:

- The upload path writes to a bucket and stores the returned key on the row that today stores a filename.
- The serving path stops reading bytes off local disk. For private user documents, keep the bucket closed and issue short-lived presigned URLs, valid for minutes rather than days, so the browser fetches directly instead of streaming through your application. If some files are public and frequently read, put a CDN in front of the bucket.
- A backfill job copies the existing 200GB across and rewrites the references.

Sequence it so the cutover is dull: send new uploads to the bucket while the read path checks the database reference and falls back to local disk when there isn't one, run the backfill against the remaining files, then delete the fallback. Every step is reversible on its own, and you never need downtime or a big-bang switch.

One tempting alternative is worth naming so you can reject it deliberately. You can pin each user to a fixed machine so their files are always local, and it appears to work right up until a deploy, a machine replacement, or an added fourth machine leaves a user's files on a box they no longer reach. Rebalancing then becomes a manual chore with no natural end.

If a cloud provider is off the table for regulatory or hosting reasons, MinIO speaks the S3 API and can run on your own hardware. You are back to operating a storage system, which is the cost you were trying to avoid, but your application code ends up identical to the hosted version and stays portable if the constraint lifts later.