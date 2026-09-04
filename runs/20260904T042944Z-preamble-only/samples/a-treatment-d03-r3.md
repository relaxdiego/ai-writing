# Store uploaded files in an object storage service

## Status

Accepted. Migration scheduled for November.

## Context

Uploaded files are written to the local disk of the single machine that serves the site, which works only because that machine both receives the upload and answers every later request for it. We are moving to three machines behind a load balancer, and that breaks the assumption: a file uploaded through one machine does not exist on the other two, so a request for it fails whenever the load balancer routes the reader to a machine other than the writer. Whatever we choose has to let any of the three machines serve any file, and has to stop any single machine from being the only place a file exists.

## Decision

We will store uploaded files in a storage service accessed over the network, keeping only a reference to each file in our database.

| Option | Monthly cost at our size | Single point of failure | Backup and versioning |
|---|---|---|---|
| Shared network drive mounted on all three machines | ~$40 | Yes, the mount | Ours to build |
| Storage service, reference in the database | ~$6 | No | Provided by the service |
| Files as binary columns in the database | Not priced | No | Multiplies the existing 200 GB backup |

Three things decided it. The storage service needs no machine to be special, so we can add, replace or lose a machine without moving data with it, which is precisely the property that local disk lacks. Backup and versioning arrive as part of the service rather than as code we would have to write, test and keep working. And at our size it costs about $6 a month against about $40 for the network drive.

The shared drive was rejected because it puts back the single point of failure we are moving to three machines to remove. All three would depend on one mount, and the mount becoming unavailable takes the whole site with it, so we would have paid roughly seven times as much for a system that fails in the same way the current one does.

The database option was rejected on backups. At 200 GB they are already slow enough to be a problem we discuss, and moving file contents into the same database would multiply the size of every backup and every restore, making the slowest thing we own slower in proportion to how much our users upload.

## Consequences

We accept three costs, all of them known in advance:

- Reading a file now crosses the network rather than coming off local disk, so a download starts more slowly. The difference is in the time to first byte rather than in throughput, and it applies to every file read, not only to large ones.
- Local development needs either real credentials to the service or a stand-in that speaks the same protocol. Neither is free: credentials have to be issued and scoped, and a stand-in has to be kept close enough to the real service that code working against one works against the other.
- The 200 GB already on disk has to be migrated. We expect the copy to take a weekend, and we expect to need the site in a read-only state for about an hour while the last changes are reconciled and the reference is switched over.