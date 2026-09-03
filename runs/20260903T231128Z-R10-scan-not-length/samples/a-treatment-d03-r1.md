# ADR: Uploaded files move to a storage service

## Status

Accepted. Migration scheduled for November.

## Context

Uploaded files are written today to the local disk of the single machine that serves the site. We are moving to three machines behind a load balancer, and at that point local disk stops functioning as storage: a file uploaded through one machine does not exist on the other two, so whether a later download succeeds depends on which machine the load balancer happens to pick. Roughly 200 GB of files are already on disk and have to end up wherever we choose. Our database backups are already slow at that volume, which rules against any option that adds the file data to the database.

## Decision

Uploaded files will be stored in a storage service accessed over the network, with only a reference to each file kept in our database.

## Options considered

- **Shared network drive mounted on all three machines.** Keeps file access looking like the filesystem code we already have, at roughly $40 a month for our volume. It puts back the failure we are moving to three machines to remove: the drive is one thing whose loss takes all three machines out together, and the mount makes the storage a fixed dependency that every new machine has to be given.
- **Storage service over the network, reference in the database.** No machine holds the files, so machines can be added, replaced, or lost without moving data first. Backup and versioning arrive with the service instead of being written and maintained by us. Cost at our volume is roughly $6 a month.
- **Binary columns in the database.** Gives a single transactional store and a single backup path, but loads 200 GB of file data into the database whose backups are already our slowest operational job, multiplying the runtime of a problem we already have. Rejected on that ground.

## Consequences

Reading a file now crosses the network rather than coming off local disk, so downloads start more slowly than they do today. The added latency is at the beginning of the transfer rather than spread through it, which matters most for small files fetched frequently and least for the large ones that dominate our volume.

Local development no longer works against a plain directory. Each developer needs either credentials for the real service or a stand-in that speaks the same interface, and whichever we pick has to be set up on new machines and kept working as the service's client library changes. This is a recurring cost on the development environment, not a one-time setup.

The 200 GB already on disk has to be moved. We expect the copy to take a weekend, with the site read-only for about an hour while the last writes are drained and the reference column is switched over. Uploads are unavailable during that hour and existing files remain readable throughout. The migration is scheduled for November.