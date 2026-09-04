# Uploaded files move to a storage service accessed over the network

Status: accepted. Migration scheduled for November.

## Context

Uploaded files are currently written to the local disk of the single machine that serves the site, and about 200 GB has accumulated there. We are moving to three machines behind a load balancer, which breaks that arrangement outright: a file uploaded to one machine does not exist on the other two, so whether a download succeeds depends on which machine the load balancer happens to route it to. Every option below is a way of giving all three machines the same view of the same files.

## Decision

We will store uploaded files in a storage service accessed over the network, keeping only a reference to each file in our database.

Three properties decided it. No machine has to be special, so we can add, replace or lose a machine without moving any data with it, which is what the move to three machines was for in the first place. The service gives us backup and versioning as part of what we are already paying for, so neither has to be built or maintained by us. At our size the cost is roughly $6 a month, against about $40 for the shared network drive.

## Options considered

- **Shared network drive mounted on all three machines.** Workable, and closest to the code we have today, but it reintroduces the single point of failure we are moving away from: the three machines stay up only as long as the one drive does. It also costs about $40 a month against $6, and backup and versioning would be ours to build.
- **Storage service with a reference in the database.** Chosen, for the reasons above.
- **Files as binary columns in the database.** Rejected on backup cost. Our database backups are already slow, and folding 200 GB of file data into them would multiply that time, making the recovery path worse for every part of the system rather than just for uploads.

## Consequences

We are accepting three costs.

- **Downloads start more slowly.** Reading a file now crosses the network instead of coming off local disk, so time-to-first-byte goes up. Throughput after that is not our concern at current file sizes, but anything that reads many small files in a loop will feel it.
- **Local development needs setup it did not need before.** A developer needs either credentials for a real bucket or a stand-in service running locally. Whichever we pick has to be in the standard setup instructions before the migration, not after.
- **The existing 200 GB has to be moved.** We expect the copy to take a weekend. The site must be read-only for about an hour of that, to cover the window between the final sync and the cutover, so uploads arriving during the copy are not stranded on the old disk.

## Migration

The move is scheduled for November. The read-only hour needs an announced maintenance window, and the old local files should be kept in place until we have confirmed the copy, so that a failed cutover is a rollback rather than a recovery.