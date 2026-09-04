# Uploaded files live in an object storage service, not on local disk

**Status:** Accepted. Migration scheduled for November.

## Context

Uploads are currently written to the local disk of the one machine that serves the site, and there are about 200 GB of them. We are moving to three machines behind a load balancer, which breaks that arrangement outright: a file uploaded to one machine does not exist on the other two, so whether a download succeeds depends on which machine the load balancer happens to pick. This is not a degradation we can tune around, and it lands the day the second machine takes traffic. Whatever we choose has to be readable and writable from all three machines, and has to keep working as machines are added and replaced.

## Options considered

A shared network drive mounted on all three machines is the smallest change to the application: the code keeps writing to a filesystem path, and the path happens to be remote. It also reintroduces exactly the failure mode we are moving to three machines to remove. The drive becomes a single component whose loss takes down uploads and downloads on every machine at once, and one machine or one mount point ends up being special in a way we then have to operate around.

A storage service reached over the network, with only a reference to each object kept in our database, requires the application to stop treating uploads as files on a path. In exchange, no machine holds any upload, so machines can be added, rebuilt, or replaced without moving data or draining anything first. Backup and versioning come with the service rather than being something we build, schedule, and then discover is broken during an incident.

Storing files as binary columns in the database keeps everything in one system with one backup and one consistency story. Our backups are already slow at 200 GB, and this option folds the entire upload corpus into that same job and grows it with every upload. The cost falls on the operation we most need to stay fast and reliable.

| | Shared network drive | Storage service | Binary columns in the database |
|---|---|---|---|
| Cost at our size | ~$40/month | ~$6/month | No new line item |
| Single point of failure | Yes, the drive | No | Shared with the database |
| Backup and versioning | We build both | Provided | Inherits the database's |
| Effect on database backups | None | None | Multiplies a job already slow at 200 GB |
| Machines are interchangeable | Not quite | Yes | Yes |

## Decision

We will store uploaded files in the storage service and keep only a reference to each object in our database.

The reasons that decided it, in the order they weighed: no machine has to be special, so we can add or replace machines without moving data; backup and versioning arrive without us writing either; and the cost at our size is roughly $6 a month against about $40 for the network drive. The shared drive was rejected because it puts back the single point of failure we are trying to remove, and the price difference only confirmed a choice already made on availability. The database option was rejected on backup time alone.

## Consequences

Reads now cross the network instead of coming off local disk, so a download takes longer to start. This is a latency cost on the first byte rather than a throughput cost, and it applies to every download, including ones that used to be served from a warm page cache.

Local development no longer works against a plain directory. Each developer needs either credentials to a real bucket or a stand-in service running locally, and the setup instructions and CI configuration have to cover whichever we standardise on.

The 200 GB already on disk has to be migrated. We expect the copy to take a weekend, and we expect to need roughly an hour of read-only operation to move the last of it and cut over without losing uploads written during the transfer. That window is the part of the plan most likely to be wrong, and it should be rehearsed against a copy before November.