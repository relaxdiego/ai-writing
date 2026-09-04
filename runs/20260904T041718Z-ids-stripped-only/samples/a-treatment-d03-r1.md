# Store uploaded files in a network storage service

## Status

Accepted. Migration scheduled for November 2026.

## Context

Uploaded files are written to the local disk of the single machine that serves the site. We are moving to three machines behind a load balancer, and local disk does not survive that move: a file uploaded to one machine is simply missing on the other two, so roughly two thirds of requests for any freshly uploaded file will fail.

Whatever replaces local disk has to be reachable from all three machines, and it has to stay reachable as we add or replace machines. We currently hold about 200 GB of uploads, and our database backups are already slow at that volume, which constrains the options below.

## Options considered

We looked at three ways to give all three machines a common view of uploaded files.

A shared network drive mounted on all three machines is the smallest change to the code, since files stay behind a filesystem path. It costs about $40 a month at our size, and it reintroduces exactly the thing this migration is meant to remove: one host whose loss takes the whole site's uploads with it.

A storage service accessed over the network, with only a reference stored in our database, keeps the files entirely outside the machines that serve the site. It costs about $6 a month at our size and provides backup and versioning as part of the service.

Storing files as binary columns in the database keeps everything in one system and one backup. It also folds 200 GB of file data into a backup process that is already slow at that size, and it multiplies that cost as uploads grow.

| | Network drive | Storage service | Database columns |
|---|---|---|---|
| Cost at our size | ~$40/month | ~$6/month | Included, but see backups |
| Single point of failure | Yes, the drive host | No | The database, already load-bearing |
| Backup and versioning | We write it | Provided | Inherits database backups |
| Effect on database backups | None | None | Multiplies a 200 GB backup that is already slow |
| Machines need special setup | Mount on every host | Credentials only | None |

## Decision

We will store uploaded files in the network storage service and keep only a reference to each file in our database.

The decisive property is that no machine is special. Nothing is mounted, nothing is pinned to a host, and no data has to move when we add, replace, or lose a machine, which is what makes the three-machine deployment work and what keeps the fourth machine cheap to add later. Backup and versioning come with the service rather than being work we schedule and maintain, and at our size the option that removes the single point of failure is also the one that costs roughly a sixth as much per month.

## Consequences

Reads now cross the network instead of coming off local disk, so a download starts more slowly than it does today. The change is in time-to-first-byte rather than throughput, and it applies to every file read, not only to uploads.

Local development no longer works against a bare filesystem. Each developer needs either credentials for the service or a stand-in that speaks the same interface, and the setup instructions have to cover whichever we choose.

The 200 GB already on disk has to be copied into the service. We expect the migration to take a weekend, with the site read-only for about an hour while the final delta is copied and the reference records are written. That read-only window is the part of the plan that needs to be announced ahead of time.