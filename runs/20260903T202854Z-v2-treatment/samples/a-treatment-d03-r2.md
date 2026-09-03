# Uploaded files move to a storage service

**Status:** Accepted. Migration scheduled for November 2026.
**Date:** 2026-09-04

## Context

Uploaded files are currently written to the local disk of the single machine that serves the site. We are moving that site onto three machines behind a load balancer, and at that point local disk stops working: a file uploaded to one machine does not exist on the other two, so whether a later request for it succeeds depends on which machine the balancer happens to pick. Any storage scheme that keeps files on a particular machine has to make that machine special, and having one machine that everything depends on is precisely the property the move to three machines is meant to remove.

The existing data is about 200 GB, and our database backups are already slow at that size. Both figures constrain the options below.

## Decision

We will store uploaded files in a storage service accessed over the network, keeping only a reference to each file in our database.

Three properties decided it. No machine has to be special, so we can add, replace, or lose a machine without moving data or draining it first, which keeps the load-balanced topology honest. Backup and versioning come with the service, so we do not write, schedule, or test either one ourselves. And at our size the service costs roughly $6 a month, against about $40 a month for the shared network drive we compared it to.

## Alternatives considered

- **Shared network drive mounted on all three machines.** Rejected. It works, but it reintroduces a single point of failure: all three machines then depend on one mount, so we would have removed the special machine only to install a special disk. It is also about seven times the monthly cost of the storage service, and backup and versioning would remain our problem to build.
- **Binary columns in the database.** Rejected. Our backups are already slow at 200 GB, and moving file bytes into the database would multiply the size of every backup and restore. The operational cost lands on the one system we least want to make slower.

## Consequences

We accept the following costs, all of them known in advance rather than discovered later:

- **Reads go over the network.** A download no longer starts by reading local disk, so there is added latency before the first byte. This affects start-up time per file rather than throughput.
- **Local development needs credentials or a stand-in.** Developers will either hold credentials for a development bucket or run a local service that emulates the storage API. Whichever we pick has to be set up before the migration, not during it.
- **The existing 200 GB has to be migrated.** We expect the copy to take a weekend, with the site read-only for roughly an hour while the final delta is moved and the application is switched over to references. The read-only window needs to be announced.