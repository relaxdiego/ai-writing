# ADR: Uploaded files move to a network storage service

**Status:** Accepted. Migration scheduled for November 2026.

## Context

Uploaded files are written to the local disk of the single machine that serves the site. We are moving to three machines behind a load balancer, and local disk does not survive that move: a file uploaded to one machine is absent on the other two, so whether a later request finds the file depends on which machine the load balancer happens to pick. We need storage that all three machines read and write equally, and we would prefer that adding or replacing a machine not involve moving any data.

## Decision

Uploaded files are stored in a storage service accessed over the network. The database keeps only a reference to each file, not its bytes.

## Options considered

| Option | Cost per month at our size | Single point of failure | Backup and versioning | Effect on database backups |
| --- | --- | --- | --- | --- |
| Storage service over the network | ~$6 | None introduced | Provided by the service | None |
| Shared network drive mounted on all three machines | ~$40 | The drive itself | Ours to build and operate | None |
| Binary columns in the database | Carried in the database tier | The database, already accepted | Rides the existing backup | Multiplies a backup already slow at 200 GB |

The storage service wins on the property we are actually buying with the load balancer, which is that no machine is special. Any of the three can serve any file, and a fourth machine joins by starting up rather than by copying 200 GB. Backup and versioning come with the service instead of being work we schedule and then have to trust. The cost difference reinforces the choice without being the reason for it: roughly $6 a month against about $40 for the shared drive.

The shared network drive was rejected because it reintroduces the failure we are spending this migration to remove. Three machines behind a load balancer that all depend on one drive have one drive's availability, and we would then own the drive's backup story as well.

Binary columns in the database were rejected on the backup window. Our backups are already slow at 200 GB, and moving the file bytes into the database would multiply that figure by whatever the uploads grow to, making every restore and every schema migration slower for as long as we keep the design.

## Consequences we accept

- **Reads go over the network.** A download no longer starts from local disk, so it starts more slowly. The steady-state transfer is unaffected; the added latency is at the beginning of each read.
- **Local development needs a stand-in.** Developers need either credentials to the real service or a local service that speaks the same protocol. We have not yet chosen between the two, and that choice is not settled by this record.
- **The existing 200 GB has to move.** We expect the migration to run over a weekend, with the site read-only for about an hour while the final sweep copies files uploaded during the bulk transfer and the references are cut over.