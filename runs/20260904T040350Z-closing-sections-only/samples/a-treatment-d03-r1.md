# Uploaded files move to a storage service

**Status:** Accepted. Migration scheduled for November.

## Context

Uploaded files are written to the local disk of the single machine that serves the site. We are moving to three machines behind a load balancer, which breaks that arrangement on the first day: a file uploaded to one machine does not exist on the other two, so whether a download succeeds depends on which machine the load balancer happens to pick. About 200 gigabytes are on disk today, and our database backups are already slow at that size.

## Decision

Uploaded files will live in a storage service accessed over the network, with only a reference to each file kept in our database.

Three properties decided it. No machine has to be special, so we can add, replace or lose an application server without moving any data with it, which is the same property that makes the load balancer worth having in the first place. The service gives us backup and versioning as part of what we are already paying for, so neither is code we write, test and then discover has been failing quietly. And at our size it costs roughly $6 a month against about $40 for a shared network drive.

## Options considered

| Option | Cost/month | Single point of failure | Backup and versioning | Effect on DB backups |
|---|---|---|---|---|
| Storage service (chosen) | ~$6 | None | Included | None |
| Shared network drive | ~$40 | The drive | We build it | None |
| Binary columns in the database | Storage plus backup time | The database | Included | Multiplies 200 GB |

The shared network drive is the closest alternative and fails on the same ground we are leaving local disk for. Mounting one drive on all three machines puts a single point of failure straight back in, so the fleet survives the loss of any application server but not the loss of the drive, and we would have paid about seven times as much for that.

Storing files as binary columns keeps everything in one system, which is a real advantage for consistency and for restores. It costs too much here. Our backups already run slowly at 200 gigabytes, and folding the file bytes into the database multiplies the volume that every full backup, every restore drill and every replica rebuild has to move.

## Consequences

We are accepting three costs.

- **Slower first byte on download.** Reads go over the network instead of off local disk, so a download starts more slowly. Throughput once it is running is not the concern; the added latency at the start is.
- **Local development needs a stand-in.** A developer running the site needs either credentials for the real service or a local substitute that speaks the same API. Whichever we pick has to be set up on every machine and kept working, and it is one more thing that can be wrong when someone new starts.
- **A migration of the existing 200 gigabytes.** The files on disk today have to be copied and their references written into the database.

We expect the migration to take a weekend, with the site read-only for about an hour while the last of the files are copied and the references are cut over. The read-only window is the part users will notice, so it is scheduled for November and will be announced ahead of it.