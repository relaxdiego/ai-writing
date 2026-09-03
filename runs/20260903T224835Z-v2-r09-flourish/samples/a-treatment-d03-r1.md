# Uploaded files move to a network storage service

**Status.** Accepted. Migration scheduled for November.

## Context

Uploaded files are written to the local disk of the one machine that serves the site. We are moving to three machines behind a load balancer, and local disk does not survive that change: a file uploaded through one machine does not exist on the other two, so whether a later request finds it depends on which machine the balancer happens to pick. Roughly 200 GB of files are on disk today, and our database backups are already slow at that volume, which constrains any option that would put the files into the database.

## Decision

Uploaded files will live in a storage service reached over the network. The database keeps only a reference to each file, not its bytes.

The property that decided it is that no machine is special. Any of the three can serve any upload, and we can add, rebuild, or replace a machine without moving data onto it first. The service also gives us backup and versioning that we would otherwise have to write and maintain ourselves. At our size it costs about $6 a month, against about $40 for the shared drive.

## Options considered

- **Storage service over the network, reference in the database (chosen).** No machine holds data that another machine needs. Backup and versioning come with the service. About $6 a month at current volume.
- **Shared network drive mounted on all three machines.** Workable, but it puts a single point of failure back into the system, which is the condition we are moving to three machines to escape. If the drive is unavailable, all three machines lose uploads at once. It also costs about $40 a month, roughly six times the storage service.
- **Files as binary columns in the database.** Rejected on backup cost. We are already slow to back up at 200 GB, and folding the uploads into the database would multiply that figure and that duration, making an operation that is already painful worse on every run.

## Consequences

Reads become network reads. A download that previously started off local disk now starts after a round trip to the storage service, so the time to first byte goes up. We accept this: the files are user uploads served on request, not hot-path data, and the latency is bounded by ordinary network behaviour rather than by anything we would have to tune.

Local development gets more setup. A developer either needs credentials for the real service or a stand-in that speaks the same interface, where before they needed only a writable directory. Whichever we settle on has to be part of the standard development environment, not something each person arranges for themselves.

The 200 GB already on disk has to be moved. We expect the copy to take a weekend, and we expect to need the site read-only for about an hour so that no upload lands on local disk after its directory has been copied. That read-only window is the part users will notice, and it is the piece of the migration plan that needs to be scheduled and announced rather than simply run.