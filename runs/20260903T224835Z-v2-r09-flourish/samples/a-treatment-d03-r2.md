# Uploaded files move to a network storage service

**Status:** Accepted. Migration scheduled for November.

## Context

Uploaded files are written today to the local disk of the single machine that serves the site. We are moving to three machines behind a load balancer, and local disk does not survive that move: a file uploaded to one machine does not exist on the other two, so whether a later request finds the file depends on which machine the load balancer happens to pick. There are roughly 200 GB of files on disk today, and that volume already shapes what our backups can do in a night.

## Decision

Uploaded files will be stored in a network storage service, with only a reference to each file kept in our database.

The property that decided it is that no machine has to be special. Any of the three can serve any file, and we can add a fourth or replace a failed one without moving data or thinking about which machine held what. The service also gives us backup and versioning as part of what we are buying, rather than as two more pieces of infrastructure we would have to write, schedule and then test. At our size the cost is around $6 a month, against about $40 for a shared network drive.

We considered two alternatives:

- **A shared network drive mounted on all three machines.** It solves the visibility problem, but it puts a single point of failure back into the system, which is the condition we are moving to three machines to get rid of. It also costs roughly seven times as much at our current volume.
- **Storing files as binary columns in the database.** Our backups are already slow at 200 GB. Folding the files into the database would multiply the size of every backup and restore, and would make the slowest thing we own slower still.

## Consequences

Reads now cross the network instead of coming off local disk, so a download begins more slowly than it does today. The difference is in the time to first byte rather than in throughput, and it applies to every file served.

Local development no longer works against a bare filesystem. Each developer needs either credentials for the real service or a stand-in that speaks the same protocol locally, and whichever we pick becomes part of the setup instructions for a new machine.

The 200 GB already on disk has to be migrated. We expect the copy to run over a weekend, with the site read-only for about an hour while we cut over so that no upload lands on the old disk after we stop copying from it.