# Uploaded files move to a storage service

**Status:** Accepted. Migration scheduled for November.

## Context

Uploaded files are written to the local disk of the single machine that serves the site, which works for exactly as long as there is one machine. We are moving to three behind a load balancer, and at that point local disk stops being somewhere a file can live: an upload handled by one machine leaves a file the other two cannot see, so whether a later download succeeds depends on which machine the load balancer happens to pick. We need a home for uploads that all three machines reach identically, and we need it before the second and third machines take traffic. About 200 GB of files already sit on the existing disk and have to move wherever we land.

## Options considered

| | Shared network drive | Storage service, reference in DB | Binary columns in the DB |
|---|---|---|---|
| Machine that must be special | the drive host | none | none |
| Single point of failure | yes, the drive | none added | none added; the database is already shared |
| Backup and versioning | we would write both | provided | inherited from database backups |
| Cost at our size | about $40 a month | about $6 a month | not costed separately |
| Effect on database backups | none | none | multiplies a 200 GB backup that is already slow |

The shared drive fails on the ground we are moving for. Putting one host in the path of every read and write reintroduces the single point of failure that the three-machine arrangement exists to remove, and it costs roughly seven times the storage service to do so. The database option fails on backups: 200 GB is already slow to back up, and folding the file bytes into the same database multiplies the size of the thing we are least happy with today.

## Decision

Uploaded files go to a storage service accessed over the network, with only a reference held in our database.

No machine is special under this arrangement, so we can add, replace or lose a machine without moving any data, which is what makes the three-machine setup worth having. Backup and versioning come with the service rather than being code we write and then have to trust. At our current size it costs about $6 a month against about $40 for the network drive, and the gap widens rather than narrows as we grow.

## Consequences

Three costs come with this and we are taking them:

- **Reads go over the network.** A download no longer starts from local disk, so it starts more slowly. This affects the time to first byte on every file we serve.
- **Local development needs a stand-in.** Developers need either credentials for the real service or a local substitute that speaks the same interface. Whichever we pick becomes a thing new joiners have to set up before they can run the site.
- **The existing 200 GB has to migrate.** We expect the copy to take a weekend, and the cutover requires the site to be read-only for about an hour while the last files move and the references are switched over.

The migration is scheduled for November.