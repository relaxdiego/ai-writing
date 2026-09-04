# Uploaded files move to a storage service

**Status:** Accepted. Migration scheduled for November.

## Context

Uploaded files are written to the local disk of the single machine that serves the site. That works only because there is one machine. We are moving to three machines behind a load balancer, and at that point local disk stops being a viable store: a file uploaded to one machine does not exist on the other two, so whether a later download succeeds depends on which machine the load balancer happens to pick. We need a store that every machine sees identically, and we need it in place before the third machine takes traffic.

We already carry 200 gigabytes of uploads on disk, and our backups of that data are slow today. Any option that grows the backup, or that makes one machine responsible for the data, works against the reason we are adding machines in the first place.

## Decision

Uploaded files will be stored in a storage service accessed over the network. The database keeps only a reference to each file, not its contents.

Three reasons decided it. No machine has to be special, so we can add, replace or lose a machine without moving data or electing a new owner for it. The service gives us backup and versioning as properties of the store rather than as software we write and maintain. At our size it costs roughly $6 a month, against about $40 for the shared network drive, and the gap widens as uploads grow.

## Alternatives considered

- **A shared network drive mounted on all three machines.** It solves visibility, but it reintroduces a single point of failure, which is the condition we are moving to three machines to remove. It also costs about $40 a month, near seven times the storage service, for a worse availability story.
- **Binary columns in the database.** Our backups are already slow at 200 gigabytes, and putting file contents in the database multiplies exactly the number that is already hurting. It would also couple every restore and every schema migration to the full weight of the upload corpus.

## Consequences

Reads now cross the network instead of coming off local disk, so a download takes measurably longer to start. Throughput once a transfer is underway is not the concern; the added latency at the beginning of each request is.

Local development no longer has a store that simply exists. Each developer needs either credentials to the real service or a stand-in service running locally, and one of those has to be chosen and documented before the migration lands, not after.

The 200 gigabytes already on disk have to be moved. We expect the copy to take a weekend, with the site read-only for about an hour while we cut over and confirm that references resolve against the new store.