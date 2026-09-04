# ADR: Store uploaded files in a network storage service

**Status:** Accepted. Migration scheduled for November.

## Context

Uploaded files are currently written to the local disk of the single machine that serves the site, and the application reads them back from that same path. We are moving to three machines behind a load balancer, which breaks that arrangement outright: a file uploaded through one machine does not exist on the other two, so whether a later request finds it depends on which machine the load balancer happens to pick. Any option we choose has to make the same file reachable from all three machines, and it has to keep working as we add or replace machines, since removing the site's dependence on one particular machine is the reason for the move in the first place. We hold about 200 GB of uploads today.

## Options considered

| | Shared network drive | Storage service, reference in DB | Binary columns in the DB |
|---|---|---|---|
| Cost per month at our size | ~$40 | ~$6 | Not billed separately |
| Reachable from all three machines | Yes | Yes | Yes |
| Single point of failure | Yes, the drive | No | The database, already present |
| Backup and versioning | We build it | Provided | Inherits DB backups |
| Effect on DB backups | None | None | Multiplies a 200 GB backup |
| Read latency | Network | Network | Network |

## Decision

We will store uploaded files in a storage service accessed over the network, keeping only a reference to each file in our database.

The service needs no machine to be special. Every machine talks to the same endpoint with the same credentials, so we can add, replace or lose a machine without moving any file data, which is exactly the property the migration to three machines is meant to buy. It also gives us backup and versioning as part of the product rather than as something we design, write and then have to test. At our current size it costs roughly $6 a month against about $40 for the network drive.

The shared network drive was rejected on the architectural point rather than the price. Mounting one drive on all three machines reintroduces a single component whose failure takes down uploads and downloads everywhere, which is the failure mode we are moving away from, and it costs about seven times as much to reintroduce it.

Storing files as binary columns in the database was rejected because of what it does to backups. At 200 GB our backups are already slow, and folding the file data into the same database would multiply that volume, making an already uncomfortable restore time considerably worse.

## Consequences

Reads now cross the network instead of coming off local disk, so a download starts more slowly than it does today. The transfer itself is not the concern; the added latency before the first byte is.

Local development no longer works against a bare filesystem. Each developer will need either credentials for a development bucket or a stand-in service running locally, and whichever we pick becomes part of the setup instructions for the project.

We have to move the 200 GB already on disk. We expect the copy to take a weekend, with the site read-only for about an hour while we cut over the references and confirm the new locations resolve. Uploads are unavailable during that window; browsing and reading continue.