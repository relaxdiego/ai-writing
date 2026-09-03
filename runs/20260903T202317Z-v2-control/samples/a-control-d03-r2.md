## ADR 0001 — Store uploaded files in an object storage service

**Status:** Accepted — 2026-09-04. Migration scheduled for November.

### Context

Uploaded files are currently written to the local disk of the single machine that serves the site. We are moving to three machines behind a load balancer. Local disk does not survive that change: a file uploaded to one machine is simply absent on the other two, so whether a user can retrieve their own upload depends on which machine the load balancer happens to route them to.

There are roughly 200 GB of existing uploads on that disk. Whatever we choose has to hold them, and we have to get them there.

### Options considered

**A shared network drive mounted on all three machines.** Every machine sees the same filesystem, so the application code barely changes. But it costs about $40 a month at our size, and it reintroduces exactly the thing this migration exists to remove: one box whose failure takes the site down. We would have traded a single application server for a single storage server.

**Files as binary columns in the database.** Consistent and transactional, and it needs no new infrastructure. Rejected on backup cost. Our backups are already slow at 200 GB; folding the uploads into the database multiplies the volume that every backup and restore has to move, and makes the restore path for a routine schema problem depend on shipping all the file data too.

**A storage service over the network, with only a reference stored in the database.** Chosen.

### Decision

Uploaded files go to a network-accessed storage service. The database stores a reference to each object, not its bytes. No file data is written to local disk as durable state.

The reasons that decided it:

- **No machine is special.** Any of the three servers can serve any file, and we can add, replace, or lose a machine without moving data or reconciling anything. This is the property the load balancer change was for.
- **Backup and versioning come with it.** We get both without writing or operating either, which is a meaningful amount of code we now do not maintain.
- **Cost.** Roughly $6 a month against about $40 for the network drive.

### Consequences

**Reads go over the network.** A download that used to come off local disk now starts more slowly. We expect this to show up as added latency at the start of a transfer rather than reduced throughput, and it applies to every file read, not just cold ones.

**Local development needs something extra.** A developer either holds credentials against a real bucket or runs a stand-in service locally. Either way, "clone and run" is no longer sufficient, and we will need to document the setup and keep it working.

**We have to migrate 200 GB.** We expect the copy to take a weekend. The site must be read-only for about an hour while we cut over — long enough to finish the tail of the copy and switch the application to reading references instead of paths, without new uploads landing on disk behind us.

**The database schema and the upload path change.** Code that touches a filesystem path becomes code that resolves a reference. This is the bulk of the application work.

**Failures become network failures.** A storage outage now makes uploads and downloads fail while the rest of the site stays up, which is a different failure shape than we have handled before and one we should have monitoring for before the cutover, not after.

### Notes

This record does not name a specific provider. That choice is compatible with the reasoning above but should be recorded separately, along with the region, the bucket layout, and how credentials reach the three machines.

---

I've written this as prose rather than saving it — say the word and I'll drop it in a file (`docs/adr/0001-object-storage-for-uploads.md` or wherever your ADRs live) once you tell me the path and numbering convention you're using.