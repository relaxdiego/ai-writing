# Store uploaded files in a storage service rather than on local disk

Status: Accepted. Migration scheduled for November.

## Context

Uploaded files are written today to the local disk of the single machine that serves the site, which works only because there is exactly one machine and every request lands on it. We are moving to three machines behind a load balancer, and that assumption breaks immediately: a file uploaded through one machine does not exist on the other two, so whether a later download succeeds depends on which machine the load balancer happens to pick. We need a location for uploads that all three machines see identically, and that keeps seeing them identically as machines are added, replaced, or lost.

Two properties of the current system shape the choice. The site already holds about 200 GB of uploads, so whatever we pick has to absorb that volume and we have to move it there. Our database backups are already slow at that same scale, which makes any option that grows the database a direct tax on an operation that is under strain.

## Decision

We will store uploaded files in a storage service accessed over the network, keeping only a reference to each file in our database.

## Alternatives considered

| | Monthly cost at 200 GB | Single point of failure | Backup and versioning | Effect on DB backups |
|---|---|---|---|---|
| Storage service (chosen) | ~$6 | None; no machine is special | Provided by the service | None |
| Shared network drive | ~$40 | Yes: the drive itself | We would build it | None |
| Binary columns in the database | Storage cost not the issue | Inherits the database's | Covered by DB backups | Multiplies an already slow 200 GB backup |

The shared network drive is the closest substitute for what we have now, and that is its problem. Mounting one drive on all three machines reintroduces exactly the single point of failure we are moving to three machines to remove: the drive going away takes the whole site's uploads with it, no matter how many application machines are healthy. It also costs roughly seven times as much at our current size, and leaves backup and versioning as work we would have to write and maintain ourselves.

Storing files as binary columns in the database is attractive because it needs no new infrastructure and puts uploads inside the backup and transaction guarantees we already have. We rejected it on backup cost. Our backups are already slow at 200 GB, and folding the uploads into the database would multiply that figure rather than add to it, degrading an operation we depend on and that is already the weakest part of our operational story.

The storage service wins on the property that matters most for the migration we are actually doing: no machine is special. Any of the three can serve any file, and we can add or replace machines without moving data or reconfiguring mounts. Backup and versioning come with the service rather than being ours to build, and at our size it costs about $6 a month against about $40 for the network drive.

## Consequences

We accept three costs, all of them known in advance:

- **Downloads start more slowly.** Reading a file now crosses the network instead of coming off local disk. The effect is on the start of a download rather than its throughput, and it applies to every file read, including ones that used to be effectively free.
- **Local development needs new setup.** A developer working on the application either holds credentials for the storage service or runs a stand-in service locally. Neither is free, and whichever we pick becomes a step in onboarding.
- **We must migrate 200 GB.** We expect the copy to take a weekend, with the site read-only for about an hour while we cut over so that no upload is written to a location we are no longer reading from. The read-only window is the part users will notice and needs to be announced.

The migration is scheduled for November. Until it completes, uploads remain on local disk and the move to three machines is blocked behind it.