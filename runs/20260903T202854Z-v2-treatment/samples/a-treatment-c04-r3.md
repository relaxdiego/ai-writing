Move the files to a storage service and keep only a key in your database.

A shared disk does technically work: you put the uploads on NFS or EFS or an equivalent, mount it on all three machines, and the code you have today keeps running unchanged. That is its whole appeal, and for a team of four it is not enough. You have replaced one machine's disk with a network filesystem that every machine now depends on, so a mount that hangs takes down all three at once instead of one, and diagnosing that is a specialist skill you would be buying on the day it breaks. It is also expensive for what it is: 200 GB on a managed network filesystem runs on the order of ten times the price of the same bytes in object storage, and every read still travels through your application processes.

Object storage gets you durability you do not have to think about, and it removes file serving from your app entirely. Uploads and downloads go directly between the browser and the bucket using presigned URLs your app hands out, so a large document does not occupy a web worker for the length of the transfer, and putting a CDN in front later is a configuration change rather than a project. Your volumes are small enough that cost is close to noise: 200 GB is a few dollars a month, and 10 GB a month of growth adds a few dollars a year.

The migration is the part worth planning, and it goes in this order:

1. Add storage fields to the file records: a bucket or provider name and an object key, alongside whatever path column you have now.
2. Write new uploads to both the local disk and the bucket, but keep reading from disk. This is reversible at any point.
3. Backfill the existing 200 GB with a script that copies each file, verifies it by checksum, and fills in the new columns.
4. Flip reads to the bucket, with a fallback to disk on a miss, and watch how often the fallback fires. It should go to zero.
5. Stop writing to disk, then delete the local copies once your backups of the bucket are confirmed good.

Keep the bucket private. The reason to put a reference in the database rather than a public URL is that authorisation stays in your application, where it already lives: the request arrives, you check the user owns the document, and only then do you mint a short-lived signed URL for it.

The one thing that would change this answer is code that treats uploads as a real filesystem, seeking within files or letting another process open them by path. Whole-file reads and writes of photos and documents port cleanly; anything doing random access needs rewriting before the move, not after.