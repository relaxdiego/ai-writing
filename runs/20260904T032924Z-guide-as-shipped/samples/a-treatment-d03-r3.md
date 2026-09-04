No repository files were reachable from this session, so the ADR is below as text rather than committed to a file.

---

# ADR 0007: Uploaded files live in a storage service, not on local disk

**Status:** Accepted. Migration scheduled for November.

## Context

Uploaded files are written to the local disk of the single machine that serves the site. We are moving to three machines behind a load balancer, and at that point local disk stops working: a file uploaded to one machine is absent on the other two, so any later request routed to a different machine fails to find it. Roughly 200 GB of uploads have accumulated under the current scheme, and our database backup is already slow at that size.

The move to three machines is itself motivated by removing the single machine as a point of failure, so a replacement storage design that reintroduces one would give back most of what we are paying for.

## Decision

Uploaded files go to a storage service accessed over the network. The database keeps only a reference to each file, not its contents.

## Options considered

**A shared network drive mounted on all three machines.** Solves the visibility problem and is the smallest change to application code, since files are still read and written through the filesystem. It costs about $40 a month at our size, and it puts a single point of failure back into the system: when the drive is unreachable, all three machines lose uploads at once. That is the property we are moving off one machine to eliminate.

**A storage service, with a reference in the database.** No machine is special, so we can add, replace, or lose a machine without moving any file data. Backup and versioning come with the service rather than being something we build and maintain. At our size it costs about $6 a month.

**Binary columns in the database.** Keeps files and their metadata in one place and one transaction. It also folds 200 GB of file data into a backup that is already slow at 200 GB of everything else, multiplying the time and storage of every backup we take. Rejected on that ground alone.

| | Network drive | Storage service | Database columns |
|---|---|---|---|
| Monthly cost at our size | ~$40 | ~$6 | included, but see backups |
| Single point of failure | yes | no | no |
| Backup and versioning | we write it | provided | provided, but slower |
| Effect on database backups | none | none | multiplies 200 GB backup |

## Consequences

Reading a file now crosses the network instead of coming off local disk, so downloads start more slowly. The effect is on time-to-first-byte rather than throughput, and it applies to every file read, not only the first.

Local development needs either real credentials or a stand-in service that speaks the same protocol. Whichever we choose has to be set up before a new developer can exercise upload or download paths at all.

The 200 GB already on disk has to be migrated. We expect the copy to take a weekend, with the site read-only for about an hour while we make the final pass and cut over.