# ADR 0001: Keep uploaded files in a storage service, not on local disk

Status: accepted. Migration scheduled for November.

## Context

Uploaded files are written to the local disk of the single machine that serves the site. We are moving to three machines behind a load balancer, and local disk does not survive that move: a file uploaded to one machine does not exist on the other two, so whether a download succeeds depends on which machine the load balancer happens to pick. Roughly 200 gigabytes of files are already on disk and will have to go wherever we choose. We also want the move to three machines to remove the single point of failure we have today, so any option that reintroduces one is working against the purpose of the migration.

## Options considered

- **A shared network drive mounted on all three machines.** All three see the same filesystem, and the application code barely changes. But the drive is one machine that every request depends on, which puts back the single point of failure we are removing, and it costs about $40 a month at our size.
- **A storage service accessed over the network, with only a reference to each file kept in our database.** No machine holds anything the others need. Backup and versioning come with the service rather than being ours to build. It costs roughly $6 a month at our size.
- **The files as binary columns in the database.** Consistent with the rest of our data and covered by one backup, but our backups are already slow at 200 gigabytes and this would multiply the volume they have to move.

## Decision

We will store uploaded files in the storage service and keep only a reference in the database.

The deciding property is that no machine is special. Any of the three can serve any file, and we can add, replace, or lose a machine without moving data or rebuilding state on the new one, which is precisely what the shared drive cannot offer. Backup and versioning arrive with the service, so two pieces of infrastructure we would otherwise have to write and maintain are simply not our code. The cost difference, about $6 a month against about $40, points the same way, though at these amounts it settles the question rather than raising it.

## Consequences

We accept three costs:

- Reads now go over the network rather than off local disk, so a download starts more slowly than it does today. The difference is in the time to first byte rather than in throughput.
- Local development needs either real credentials or a stand-in service, since there is no longer a directory on the developer's own disk to write into.
- The 200 gigabytes already on disk have to be migrated. We expect the copy to take a weekend, with the site read-only for about an hour while we cut over and confirm that references resolve.