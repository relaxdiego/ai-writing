Move the files to object storage and keep only a reference in your database.

The diagnosis you were given is right, and it's worth being precise about the failure so you can recognise it in the logs during the transition: an upload lands on machine A, the next request for that file is balanced to machine B, and the user gets a 404 for a photo they just watched upload successfully. It will be intermittent, roughly two-thirds of the time with three machines, and it will look like a caching bug for the first day of debugging. Sticky sessions hide it rather than fix it, because the file is still gone the moment that one machine is replaced or restarted.

Shared disk does solve the correctness problem. The reason not to reach for it is that you are a team of four and it hands you a new piece of infrastructure to own. NFS or EFS has to be provisioned, mounted at boot on every machine, monitored, and tuned when it's slow, and its failure mode is that all three machines go down together rather than one. Metadata operations over the network are far slower than local ones, so code that stats a directory in a loop gets suddenly and mysteriously slow. Somebody on the team ends up learning about stale file handles at an unwelcome hour. Object storage takes all of that off your plate for a service with an HTTP API and no operational surface of its own.

Cost is not a factor at your size. 200 GB with 10 GB a month of growth is about $5 a month on S3 standard, and a little over $6 a month two years from now. Egress is the line item that actually varies between providers, so if you serve a lot of large files to users, Cloudflare R2 or Backblaze B2 will be materially cheaper than S3 or GCS. All three speak the S3 API, so write against that and the choice stays reversible.

The migration itself is boring, which is the point:

1. Add a column for the storage key on whatever table records an upload, nullable at first.
2. Put every read and write of a file behind one small module, so the rest of the app asks for "the file for this record" rather than opening a path. This is the step that makes the rest safe, and it's worth doing on its own before anything moves.
3. Switch new uploads to write to the bucket and populate the key.
4. Backfill the existing 200 GB with a script, filling in keys as it goes. Reads fall back to local disk whenever the key is null, so the two states coexist and you can stop and restart the backfill freely.
5. Once no rows have a null key, delete the fallback branch and then the files on disk, in that order and not on the same day.

Three things genuinely get harder, and they're worth planning for rather than discovering:

- **Anything that wants a real file.** Thumbnailing, zip building, virus scanning and PDF processing all need the object downloaded to a temp file first, and that temp file needs cleaning up. If you have a library that takes a path, this is where the work is.
- **Serving the file.** You can no longer let the web server hand over a file from disk. Either issue short-lived presigned URLs from an endpoint that does the authorization check, or proxy the bytes through the app. Presigned URLs are the right default: they keep the download traffic off your machines entirely. Give them a short expiry, on the order of minutes, and remember that anyone holding the URL within that window can fetch the object.
- **Consistency between the database and the bucket.** They are now two systems that can disagree. Restoring the database to a point in time no longer restores a matching set of files, and an upload that fails after writing the object but before committing the row leaves an orphan. Write the object first and the row second, so a failure leaves an unreferenced object rather than a broken reference, and add a lifecycle rule or a weekly job that sweeps up objects nothing points at. Turn on versioning while you're there: it costs almost nothing at 200 GB and it is your undo button for a bad delete.

One security point that's easy to get for free now and painful to retrofit: serve user uploads from a separate domain, not the one your app and its session cookies live on. If someone uploads an HTML file or an SVG with script in it and you serve it from your own origin, that's stored XSS against your own users. A distinct bucket domain contains it.

The case for shared disk is narrow enough that you'll know if you're in it. It's third-party software you can't modify that insists on a POSIX path, or a workload doing heavy random seeks into large files. Photos and documents on a four-person team are not that.