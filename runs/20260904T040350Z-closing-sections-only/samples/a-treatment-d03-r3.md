# ADR: Uploaded files move to a storage service

**Status:** Accepted. Migration scheduled for November.

## Decision

Uploaded files will live in a storage service accessed over the network, with only a reference to each file held in our database. Local disk stops being a storage location for uploads, and no machine holds anything the others need.

## Context

Uploads are currently written to the local disk of the single machine that serves the site, which works only because there is one machine. We are moving to three behind a load balancer, and at that point local disk fails outright: a file uploaded to one machine is missing on the other two, so whether a download succeeds depends on which machine the load balancer happens to pick. There are roughly 200 gigabytes already on disk, and any decision here has to account for moving them.

## Options considered

- **A shared network drive mounted on all three machines.** Every machine sees the same files, and the application code barely changes. It costs about $40 a month at our size, and it puts a single point of failure back into the system, which is the specific problem the three-machine move exists to solve.
- **A storage service accessed over the network, with a reference in our database.** Files are addressed by name rather than by location, so no machine is special. Backup and versioning come with the service. Cost at our size is roughly $6 a month.
- **Binary columns in the database.** Files and their metadata stay consistent with each other and are covered by one backup process. That backup process is already slow at 200 gigabytes, and this option would multiply the volume it has to carry.

## Why the storage service

The deciding property is that it leaves no machine special. Machines can be added, replaced or lost without any data moving, which is what we need if the three-machine setup is to be worth the trouble of building it. The shared drive gives us shared access but keeps the coupling: the drive becomes the component whose failure takes the site down, and we would have spent the migration effort to relocate a single point of failure rather than remove one.

The other two reasons are smaller but point the same way. Backup and versioning are provided by the service, so we do not write or maintain them, and the running cost is about $6 a month against about $40 for the network drive. The database option was rejected on backup time alone; consistency between file and metadata is worth something, but not at the price of multiplying a backup that is already slow.

## Consequences

We are accepting three costs:

- Reads go over the network rather than off local disk, so a download starts more slowly. Throughput once started is not the concern; the added latency at the beginning of each read is.
- Local development needs either real credentials or a stand-in service that speaks the same protocol. Neither is free to set up, and new developers will hit this on their first day.
- The 200 gigabytes already on disk have to be migrated. We expect the copy to take a weekend, and we expect to need the site read-only for about an hour while the final delta is copied and the reference is switched over.

The migration is scheduled for November, with the read-only window announced in advance.