---
id: d03
register: document
name: Architecture decision record
---
Write an architecture decision record for the following decision.

We are deciding where uploaded files live. Today they are written to the local disk of the single machine that serves the site. We are moving to three machines behind a load balancer, so local disk stops working: a file uploaded to one machine is missing on the other two.

We considered a shared network drive mounted on all three machines, a storage service accessed over the network with only a reference kept in our database, and storing the files as binary columns in the database itself. We chose the storage service.

Reasons that mattered: it needs no machine to be special, so we can add or replace machines without moving data; it gives us backup and versioning without us writing either; and the cost at our size is roughly $6 a month against about $40 for the network drive. The shared drive also puts a single failure point back in, which is the thing we are trying to remove. The database option was rejected because our backups are already slow at 200 gigabytes and this would multiply that.

Costs we accepted: reading a file now goes over the network rather than off local disk, so a download starts more slowly; local development needs either credentials or a stand-in service; and we have to migrate the 200 gigabytes already on disk, which we expect to take a weekend and to require the site to be read-only for about an hour.

Status: accepted, migration scheduled for November.
