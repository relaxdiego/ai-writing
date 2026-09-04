# Uploaded files move to an object storage service

**Status:** Accepted. Migration scheduled for November.

## Context

Uploaded files are written to the local disk of the single machine that serves the site. We are moving the site to three machines behind a load balancer, and local disk does not survive that move: a file uploaded to one machine does not exist on the other two, so whether a download succeeds depends on which machine the load balancer happens to pick. There is roughly 200 GB of existing uploads on that disk, and any decision here has to account for moving it.

## Decision

Uploaded files go to a storage service accessed over the network. The database keeps only a reference to each file, not its bytes.

## Options considered

| | Monthly cost | Single point of failure | Backup and versioning | Effect on DB backups |
|---|---|---|---|---|
| Storage service (chosen) | ~$6 | None; no machine is special | Provided by the service | None |
| Shared network drive | ~$40 | Yes, the drive itself | We would build it | None |
| Binary columns in the database | Storage cost inside the DB | None | Covered by DB backups | Multiplies an already slow 200 GB backup |

Three things decided it. No machine is special under the storage service, so we can add, replace or lose a machine without moving any data, and adding machines is the reason we are here. Backup and versioning come with the service rather than being work we schedule and then maintain. The cost is roughly $6 a month against about $40 for the network drive.

The shared network drive was rejected because it reintroduces the single point of failure we are spreading three machines out to remove, at nearly seven times the cost. Storing files as binary columns was rejected because our backups are already slow at 200 GB, and folding uploads into the database would multiply that figure and the restore time with it.

## Consequences

Reading a file now crosses the network instead of coming off local disk, so a download starts more slowly than it does today. The bytes still stream at the same rate once started; what changes is the delay before the first of them arrives.

Local development needs either real credentials or a stand-in service running alongside the app. Neither is free to set up, and a developer with a fresh checkout will not be able to upload anything until one of them is in place.

We have to migrate the 200 GB already on disk. We expect the copy to take a weekend, and we expect to put the site into read-only mode for about an hour to catch the final delta and cut over.