No file tools are available in this session, so here is the ADR as text — paste it into your ADR directory and renumber the heading to fit your sequence.

---

# ADR-NNNN: Store uploaded files in an object storage service

**Status:** Accepted
**Date:** 2026-09-04
**Migration scheduled:** November

## Context

Uploaded files are currently written to the local disk of the single machine that serves the site. We are moving to three machines behind a load balancer. Local disk does not survive that move: a file uploaded to one machine does not exist on the other two, so any later request routed elsewhere fails.

We hold roughly 200 GB of uploaded files today. Database backups at that size are already slow.

We need a location for uploaded files that every machine can read and write, that does not tie us to any particular machine, and that lets us add or replace machines freely.

## Decision

Uploaded files will be stored in an object storage service accessed over the network. The database will hold only a reference to each file, not its bytes.

## Options considered

**1. Shared network drive mounted on all three machines.** Rejected. It reintroduces a single point of failure, which is the specific problem this move is meant to remove: if the drive is unavailable, all three machines lose uploads at once. It also costs about $40/month at our size.

**2. Object storage service, reference in the database.** Chosen.

- No machine is special. Machines can be added, replaced, or lost without moving data.
- Backup and versioning come with the service; we do not write or maintain either.
- Cost at our size is roughly $6/month, against about $40/month for the network drive.

**3. Files as binary columns in the database.** Rejected. Our backups are already slow at 200 GB, and moving file bytes into the database would multiply that.

## Consequences

Accepted costs:

- **Reads go over the network.** A download no longer comes off local disk, so it starts more slowly. This is a latency cost on the first byte, not a correctness problem.
- **Local development needs setup.** Developers need either credentials for the real service or a stand-in service running locally. This is new friction for anyone setting up the project.
- **A migration is required.** The 200 GB already on disk must be moved. We expect the copy to take a weekend, and we expect to need the site read-only for about an hour to catch up the tail and cut over.

Gained:

- Adding, replacing, or losing a machine no longer involves moving or recovering upload data.
- Backup and versioning of uploads are handled without code we maintain.
- Ongoing storage cost drops to roughly $6/month.

## Notes

The specific storage provider is not fixed by this decision and should be recorded separately.