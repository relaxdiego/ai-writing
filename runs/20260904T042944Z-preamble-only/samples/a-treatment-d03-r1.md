# Uploaded files move to a network storage service

**Status:** Accepted, 2026-09-04. Migration scheduled for November.

## Context

Today one machine serves the site, and uploaded files are written to that machine's local disk. We are moving to three machines behind a load balancer, and local disk does not survive the move: a file uploaded through one machine does not exist on the other two, so whether a later download succeeds depends on which machine the load balancer happens to pick. Roughly 200 GB of files are already on local disk, and the site's database backups are already slow at that size.

## Decision

Uploaded files are stored in a storage service reached over the network. The database keeps a reference to each file rather than its bytes.

## Options considered

| Option | Cost per month at our size | Single point of failure | Backup and versioning | Effect on database backups |
| --- | --- | --- | --- | --- |
| Storage service, reference in the database | ~$6 | None | Provided by the service | None |
| Shared network drive mounted on all three machines | ~$40 | The drive | We would have to build it | None |
| Binary columns in the database | Storage billed with the database | Whatever the database already has | Covered by database backups | Multiplies an already slow backup |

The storage service wins on the property we are actually buying with this migration, which is that no machine is special. Files do not live anywhere that a particular host owns, so we can add a fourth machine, or replace a failed one, without moving data or draining a host first. It also gives us backup and versioning as part of the service, which is work we would otherwise have to write and then maintain. The cost difference reinforces the choice rather than driving it: about $6 a month against about $40 for the network drive.

The shared network drive was rejected because it reintroduces exactly what the three-machine topology is meant to remove. Every machine depends on one drive, so the drive being unavailable takes down all three, and we would have spent the migration effort to arrive back at a single point of failure with a larger fleet in front of it.

Binary columns in the database were rejected on backup cost. Our backups are already slow at 200 GB, and moving file bytes into the database multiplies that figure by the size of the upload corpus and keeps multiplying it as uploads accumulate. Restore time grows with it, which is the number that matters during an incident.

## Consequences

Reads now cross the network instead of coming off local disk, so a download starts more slowly than it does today. The difference is in the time to first byte rather than in throughput, and we accept it.

Local development no longer works against a plain directory. Each developer needs either credentials for the real service or a stand-in service running locally, and whichever we choose has to be part of project setup rather than something each person solves privately.

The 200 GB already on disk has to be migrated. We expect the copy to take a weekend, with about an hour during which the site is read-only so that no upload lands on local disk after the copy has passed it. Uploads are refused for that hour; reads continue.