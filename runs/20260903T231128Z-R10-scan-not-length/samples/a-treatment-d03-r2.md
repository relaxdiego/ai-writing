# Uploaded files move to a network storage service

## Status

Accepted. Migration scheduled for November.

## Context

Uploaded files are currently written to the local disk of the one machine that serves the site, which works only because there is one machine. We are moving to three machines behind a load balancer, and at that point local disk stops being storage at all: a file uploaded through one machine does not exist on the other two, so whether a later download succeeds depends on which machine the load balancer happens to pick. Roughly 200 GB of files are on disk today, and whatever we choose has to hold that much and keep growing.

Three options were on the table: a shared network drive mounted on all three machines, a storage service reached over the network with only a reference to each file kept in our database, and the file bytes themselves stored as binary columns in the database.

## Decision

Uploaded files go to a network storage service. The database keeps a reference to each file rather than its contents, and application code reads and writes through the service's API instead of the filesystem.

## Alternatives considered

| Option | Cost at our size | Single point of failure | Backup and versioning | Effect on database backups |
|---|---|---|---|---|
| Storage service (chosen) | ~$6/month | None; no machine is special | Provided by the service | None |
| Shared network drive | ~$40/month | Yes; the drive | We would have to build it | None |
| Binary columns in the database | Not costed | The database | Covered by existing backups | Multiplies an already slow backup |

The storage service wins on the property we are actually buying with this migration, which is that no machine is special. Machines can be added, replaced or lost without anyone moving data first, and adding a fourth machine later costs nothing beyond the machine. The shared drive would work, but it reintroduces exactly the single point of failure that the move to three machines is meant to remove, and it costs about six times as much while leaving backup and versioning as work for us to write ourselves. Storing bytes in the database was rejected on backup time: our backups are already slow at 200 GB, and folding the files into them would multiply that, making the restore path worse in the same stroke.

## Consequences

We get backup and versioning without writing or operating either, and capacity planning for uploads stops being a thing we do.

The costs we are accepting:

- **Slower first byte on download.** Reads now cross the network instead of coming off local disk, so a download starts more slowly than it does today. Throughput once a transfer is running is not the concern; the added latency at the start is.
- **Local development needs setup.** A developer needs either credentials for the real service or a stand-in service running locally, where previously a scratch directory was enough. Whichever we standardise on has to be documented and checked in, or this becomes a recurring tax on new developers.
- **A migration of 200 GB.** We expect the copy to take a weekend, and the site to be read-only for about an hour while the final delta is copied and the reference column is switched over. Uploads are unavailable during that hour; reads continue.