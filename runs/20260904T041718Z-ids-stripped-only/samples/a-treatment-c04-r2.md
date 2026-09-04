Move the files to a storage service and keep a reference in the database. At your size and team size, a shared disk buys you nothing that object storage doesn't, and costs you an operational component that a team of four should not be maintaining.

The diagnosis you were given is right, and it's worth being precise about the failure so you recognise the tempting bad fix. A user uploads a photo, the load balancer sends that request to machine A, the bytes land on A's disk. The next request — the page that displays the photo — goes to machine B, which has no such file, and the user gets a broken image. The fix that suggests itself is sticky sessions, pinning each user to one machine. Don't. It makes the bug intermittent rather than absent (it comes back whenever a machine is replaced, redeployed, or scaled in), it gives you three divergent piles of files to back up, and it means losing one machine means permanently losing whatever files only lived there.

That leaves the two options you named:

| | Shared disk (NFS/EFS/managed file share) | Object storage (S3, R2, GCS, B2) |
|---|---|---|
| App changes | Almost none: paths keep working | Real: upload, read, and delete paths all change |
| Cost at 200 GB | ~$60/mo on EFS standard; a self-run NFS box is a VM plus its disk plus your time | ~$5/mo on S3 standard, less on B2/R2 |
| Failure mode | Share goes down, all three machines lose files at once | Provider-managed redundancy; effectively a non-event |
| Serving downloads | Bytes flow through your app servers | Presigned URLs; bytes never touch your app |
| Backups | Yours to build and test | Versioning and lifecycle rules are a config setting |
| Ongoing attention | Mount options, stale handles, capacity, permissions | Essentially none |

The one honest advantage of the shared disk is the first row, and it's real: you could be running on three machines by Friday. But it's a loan, not a saving. You still have to solve backups, you still own capacity planning, and you've added a component whose failure takes down all three machines simultaneously. Object storage costs you a week of work now and then asks nothing of you for years.

The cost line deserves one caveat, because storage is the cheap part and egress is where the surprise lives. S3 charges around $0.09 per gigabyte for data leaving the network, so if your users download heavily, bandwidth will exceed your storage bill by a wide margin. Cloudflare R2 and Backblaze B2 charge nothing for egress and are otherwise close enough to S3-compatible that the client library barely changes. If these are user photos being viewed repeatedly, start there, or put a CDN in front of S3.

A migration that doesn't require downtime or a flag day runs roughly like this:

1. Add a column to the files table for the storage key. Leave the existing path column alone for now.
2. Write a small storage module with `put`, `get`, `delete`, and `signed_url` behind it, and route every existing filesystem call through it. This is the bulk of the work and it's worth doing before anything touches the network.
3. Change writes only: new uploads go to the bucket and populate the key column. Reads check for a key and fall back to the local path when it's null. You are now dual-mode and correct.
4. Backfill the 200 GB with a script that walks the old rows, uploads, sets the key, and verifies by comparing sizes and checksums. Run it in batches, make it resumable, and let it take as long as it takes.
5. When no rows have a null key, delete the fallback branch, then add the third machine.
6. Keep the local files around, untouched, for a few weeks after cutover before deleting anything.

Two details that will bite during step two. Store a bucket key like `uploads/2026/09/a3f1….jpg`, not a full URL — URLs embed the provider, the region, and the CDN hostname, and every one of those will change at some point while the key never does. And any code that resizes images, extracts PDF text, or otherwise expects a local path now needs to stream the object to a temp file first, work on it, and clean up. That code is easy to miss because it usually lives in a background job rather than a request handler.

For uploads themselves, send the bytes through your app server initially. Direct browser-to-bucket uploads with a presigned PUT are better and you'll want them eventually, but they add CORS configuration, key-generation endpoints, and a validation problem (the file arrives without your app having inspected it), and none of that needs solving in the same change that unblocks your third machine.