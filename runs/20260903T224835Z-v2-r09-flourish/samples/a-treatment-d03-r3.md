# ADR: Uploaded files move to a network storage service

## Status

Accepted. Migration scheduled for November.

## Context

Uploads are written to the local disk of the one machine that serves the site. We are moving to three machines behind a load balancer, and local disk stops working the moment we do: a file uploaded through one machine does not exist on the other two, so whether a later request finds it depends on which machine the load balancer happens to pick. Anything that replaces local disk has to be reachable identically from all three machines, and it should avoid reintroducing a component whose failure takes every machine down at once, since removing that kind of dependency is much of the reason we are adding machines.

## Decision

Uploaded files will be stored in a network storage service, with only a reference to each file kept in our database.

The property that decided it is that no machine is special. Every machine reaches the same files by the same path, so we can add a fourth machine, replace a failed one, or rebuild all three without relocating file data or tracking which machine held what. The service also provides backup and versioning as part of what we pay for it, so an accidental overwrite or deletion is recoverable without us building that recovery and then keeping it working. Cost settles the remainder of the comparison: at our size the storage service is roughly $6 a month, against about $40 for the network drive.

## Options considered

- **Storage service, reference in the database (chosen).** No machine holds state the others lack; backup and versioning come with it; about $6 a month.
- **Shared network drive mounted on all three machines.** File access stays close to what the application does today, but all three machines then depend on the drive, and losing it loses uploads everywhere at once. The single point of failure we are moving to three machines to remove would be reinstalled one layer down, at about $40 a month.
- **Files as binary columns in the database.** Rejected on backups. At 200 GB our backups are already slow, and moving file bytes into the database multiplies the size and duration of every backup and every restore, which are the operations we can least afford to make worse.

## Consequences

Reading a file now crosses the network. A download that used to begin off local disk begins instead with a request to the storage service, so downloads start more slowly even though throughput once started is fine. Local development also stops being self-contained: a developer needs either credentials for the real service or a stand-in service running locally, and we will have to document and support whichever we standardise on.

Migration is the immediate cost. About 200 GB already sits on disk and has to be copied across and re-referenced, which we expect to occupy a weekend. Roughly one hour of that requires the site to be read-only, so that no upload lands on local disk after its directory has been copied. Scheduling that window, and communicating it, is part of the November work.