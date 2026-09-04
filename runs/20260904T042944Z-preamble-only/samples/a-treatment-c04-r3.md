Move the files to a storage service and keep only a reference in your database.

The breakage you were told about is real, and it is worth being precise about how it shows up. A file uploaded through machine A lands on A's disk, and the next request for that file has a two in three chance of arriving at B or C, which return a 404. You can paper over this with sticky sessions, but that only holds until a machine restarts or you deploy, and it makes losing a machine equivalent to losing every file uploaded through it. Nothing about three machines is special here; the same defect appears the moment you have two, and it also means your files are not currently backed up by anything other than whatever snapshots that one machine's disk gets.

Between your two options, shared disk is the one that costs a four-person team more over time. A network filesystem is a service you now operate: it has its own failure modes, its own performance cliffs under concurrent access, its own backup story that you have to build, and it becomes a single point of failure that all three machines depend on. Object storage has none of that, and user uploads are the workload it was designed for, since photos and documents are written once, read many times, and never modified in place. You give up POSIX semantics, which you were not using.

The cost difference points the same way. Rough list prices, worth confirming against current rates:

| Option | 200 GB today | ~560 GB in 3 years | Egress |
|---|---|---|---|
| AWS EFS (shared disk) | ~$60/mo | ~$170/mo | free within VPC, plus you still buy backups |
| AWS S3 | ~$5/mo | ~$13/mo | $0.09/GB after the first 100 GB |
| Cloudflare R2 | ~$3/mo | ~$8/mo | none |

Storage is cheap enough at your size that it should not drive the decision, but egress can, and it is the number people miss. If those photos are displayed on pages that get real traffic, bandwidth will dominate your bill on S3, and either a CDN in front of the bucket or a provider like R2 that does not charge for egress is worth choosing deliberately rather than discovering later.

The work is mostly the migration, not the new code path. A sequence that lets you ship in pieces and never take an outage:

1. Add columns to your file records for the storage key, size, content type, and a checksum, plus a marker for where the bytes currently live.
2. Send new uploads to the bucket, and make the read path check the marker so it serves old files from disk and new ones from storage.
3. Backfill the existing 200 GB in the background, flipping each row's marker as its object lands and verifies.
4. When no rows point at disk, delete the disk read path and the files.

Two details are easy to get wrong. Write the object before you write the database row, so a crash between the two leaves an unreferenced object rather than a row pointing at nothing; a periodic sweep for objects with no matching row cleans those up, and the same ordering reversed on delete, meaning row first and object later, keeps you from serving a broken reference. And do not make the bucket public. Keep your application as the authorization point and hand out short-lived signed URLs, so the check that a user may see a document stays in your code where it already is.

The case for shared disk is narrow and you should know whether you are in it: on-premises hardware with no object store available, or files that are appended to or edited in place rather than replaced. If it is the former and you would rather not depend on a cloud provider, MinIO gives you the same interface on your own machines, and your application code does not need to know the difference.