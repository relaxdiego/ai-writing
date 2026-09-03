# ADR-NNN: Uploaded files move to a storage service

## Status

Accepted. Migration scheduled for November.

## Context

Uploaded files are written to the local disk of the machine that serves the site. This works today only because there is exactly one such machine. We are moving to three machines behind a load balancer, and at that point local disk stops being a viable answer: a file uploaded through one machine does not exist on the other two, so whether a later request finds it depends on which machine the load balancer happens to route to. The failure is silent and intermittent, which is worse than an outright error. There are roughly 200 GB of uploaded files on disk today, and our database backups at that same scale are already slow enough to be a standing complaint.

## Decision

Uploaded files will be stored in a storage service accessed over the network. The database keeps only a reference to each file, not its bytes.

We considered three options:

- A shared network drive mounted on all three machines.
- A storage service over the network, with a reference in the database.
- Binary columns in the database itself.

The storage service wins on the property that motivated the whole change: no machine is special. Any of the three can serve any file, and we can add, replace, or lose a machine without moving data or rebuilding state on the replacement. It also gives us backup and versioning as part of the service, which is work we would otherwise have to write and then maintain. At our size it costs about $6 a month, against about $40 for the network drive.

The shared drive was rejected because it puts a single point of failure back into the system. Every one of the three machines would depend on one mount being healthy, so the drive going away takes the whole site with it, and that is precisely the exposure the move to three machines is meant to remove. Paying roughly seven times as much for it made the decision easy.

Binary columns in the database were rejected on backup cost. Our backups are already slow at 200 GB, and folding the file bytes into the database would multiply the volume that every backup, restore, and replica rebuild has to move. A restore that is slow now becomes a restore we cannot rely on during an incident.

## Consequences

Reads now cross the network instead of coming off local disk, so a download starts more slowly. The size of the delay is a per-request latency cost at the start of the transfer rather than a change in throughput, but it is real and users on latency-sensitive paths will notice it.

Local development no longer works with a bare checkout. Each developer needs either credentials for a real bucket or a stand-in service running locally, and whichever we choose has to be part of the standard setup instructions rather than folklore.

We have to migrate the 200 GB already on disk. We expect the copy to take a weekend, with the site read-only for about an hour while we cut over and reconcile the tail of files written during the copy. That read-only window needs to be scheduled and announced.