# Uploaded files move to a storage service

Status: accepted. Migration scheduled for November.

## Context

Uploaded files are written to the local disk of the one machine that serves the site. We are moving to three machines behind a load balancer, and local disk stops working under that topology: a file uploaded through one machine does not exist on the other two, so any later request that the balancer routes elsewhere fails to find a file the user just uploaded. There are roughly 200 GB of uploads on disk today, and our database backups are already slow at that size.

## Decision

Uploaded files will be stored in a storage service accessed over the network, with only a reference to each file held in our database.

## Options considered

| | Storage service | Shared network drive | Binary columns in the database |
|---|---|---|---|
| Cost at our size | ~$6/month | ~$40/month | No separate cost |
| Machine must be special | No | Yes, the drive host | No |
| Single point of failure | No | Yes | Shared with the database |
| Backup and versioning | Provided | We build it | Inherits database backups |
| Effect on database backups | None | None | Multiplies an already slow 200 GB |

The deciding reason was that the storage service needs no machine to be special. Machines can be added, replaced or lost without moving data, which is the property we are buying by going to three machines in the first place. The shared network drive undoes that: it reintroduces one host whose failure takes down uploads for all three machines, so we would be paying about $40 a month to put back the failure point we are trying to remove. Backup and versioning come with the storage service rather than being something we design, write and then have to trust. Binary columns in the database were rejected on backup cost alone, since folding 200 GB of uploads into a backup that is already slow at that volume makes restore times worse in exactly the situation where we need them to be good.

## Consequences

We accept three costs, none of which we expect to revisit:

- Reads now cross the network instead of coming off local disk, so a download starts more slowly. This is latency to first byte rather than throughput, and it is the direct price of files not living on any particular machine.
- Local development needs either real credentials or a stand-in service that speaks the same interface. Whichever we pick becomes a step in environment setup that did not exist before.
- The 200 GB already on disk has to be migrated. We expect the copy to take a weekend, with the site read-only for about an hour while we cut over and confirm that references resolve.

The read-only window is the part users will notice, so it should be scheduled and announced rather than absorbed quietly. After the migration, no application code should read or write the local upload path, and the path should be removed so that a stray write cannot silently produce a file that only one machine can see.