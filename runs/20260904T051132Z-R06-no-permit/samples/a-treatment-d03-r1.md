# Store uploaded files in a network storage service

**Status:** Accepted. Migration scheduled for November.

## Context

Uploaded files are written today to the local disk of the single machine that serves the site. We are moving to three machines behind a load balancer, and local disk does not survive that move: a file uploaded to one machine is absent from the other two, so whether a download succeeds depends on which machine the load balancer happens to pick. Whatever we choose has to give all three machines the same view of the same files, and has to keep giving it as machines are added, replaced, and lost. About 200 GB of uploads sit on disk now, and our database backups at that size are already slow.

## Decision

We will store uploaded files in a storage service accessed over the network, keeping only a reference to each file in our own database.

The reason that carried the most weight is that no machine becomes special. Any of the three can serve any file, and we can add a fourth or rebuild a failed one without moving a byte of user data, which is the property we are buying by moving off a single box in the first place. Beyond that, the service gives us backup and versioning as part of what we are already paying for, so an accidental overwrite or delete becomes recoverable without us designing, writing, and then maintaining that ourselves. The price settles the rest: roughly $6 a month at our current size, against about $40 for a shared network drive holding the same data.

## Alternatives considered

A shared network drive mounted on all three machines would work, and it is the smallest change to the application code, since files stay behind a filesystem path. It costs about $40 a month, and it reintroduces a single point of failure: when the drive is unreachable, all three machines lose uploads at once, which leaves us with three web servers and one thing that can take them all down. We are doing this work to remove that kind of dependency, so paying more to keep one is the wrong trade.

Storing files as binary columns in the database solves distribution neatly, because the database is already shared by all three machines and already backed up. We rejected it on backup cost. The 200 GB of uploads would move into a database whose backups are slow today, multiplying the size of every full backup and lengthening every restore, and restore time is the number that matters when we are actually using a backup.

## Consequences

Reads now cross the network instead of coming off local disk, so a download starts more slowly than it does today. The delay is in the first byte rather than in throughput, and it applies to every file the site serves.

Local development no longer works against a bare filesystem. Each developer needs either credentials for a real bucket or a stand-in service running alongside the application, and one of those has to be set up and documented before the migration lands.

We have to move the 200 GB already on disk. We expect the copy to take a weekend, with the site read-only for about an hour while we cut over and confirm that references resolve. Planning that window, and deciding what a read-only site does when someone tries to upload, is part of the November work.