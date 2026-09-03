No file tools are available in this session, so here is the ADR as text — drop it into your ADR directory with the next number in sequence.

---

# ADR: Store uploaded files in an object storage service

**Status:** Accepted — migration scheduled for November 2026
**Date:** 2026-09-04

## Context

Uploaded files are currently written to the local disk of the single machine that serves the site. We are moving to three machines behind a load balancer. Local disk stops working under that topology: a file uploaded through one machine does not exist on the other two, so any later request routed elsewhere fails.

We have roughly 200 GB of uploads already on disk. Database backups at that size are already slow enough to be a standing concern.

## Decision

Uploaded files will be stored in an object storage service accessed over the network. The database keeps only a reference to each object; the bytes never live on an application machine.

## Rationale

- **No machine is special.** Every application machine is interchangeable, so we can add, replace, or lose one without moving data. This is the property the load-balancer move exists to get.
- **Durability and versioning come with the service.** Backup and version history are provided rather than written and maintained by us.
- **Cost.** About $6/month at our current size, against roughly $40/month for a shared network drive.

## Alternatives considered

**Shared network drive mounted on all three machines.** Rejected. It reintroduces a single point of failure — the exact property we are moving to three machines to eliminate — and costs roughly $40/month against $6.

**Binary columns in the database.** Rejected. Our backups are already slow at 200 GB, and moving upload bytes into the database would multiply that volume and the time to restore.

## Consequences

Accepted costs:

- **Slower start to a download.** Reads go over the network instead of off local disk, so time-to-first-byte increases.
- **Local development needs setup.** Developers need either credentials for the real service or a stand-in service running locally. This is new friction on a fresh checkout.
- **A migration.** The 200 GB already on disk must be copied. We expect the migration to take a weekend, with the site read-only for approximately one hour during the cutover.

Ongoing:

- Storage cost becomes a recurring line item that scales with upload volume rather than a fixed disk we already own.
- Availability of uploads is now coupled to the storage service.

## Follow-ups

These are not decided here:

- Choose the local-development approach: shared credentials against a real bucket versus a local stand-in service.
- Decide how downloads are served — proxied through the application or via signed URLs pointing at the storage service — which materially affects the added latency above.
- Confirm the one-hour read-only window with whoever owns the November schedule.