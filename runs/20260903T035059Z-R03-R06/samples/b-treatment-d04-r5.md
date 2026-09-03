# Image upload failure, 2025-07-14

Image uploads failed for every user for 2 hours and 36 minutes, from 09:12 to 11:48 UTC. Roughly 18,000 upload attempts failed during that window. No data was lost: uploads were rejected before any partial write, and the clients that retried succeeded once the service recovered.

The sequence of events:

- 09:12 — `media-service` v4.7.0 deployed to production.
- 09:14 — upload error rate rises from 0.2% to 100%. No alert fires.
- 09:41 — first customer support ticket.
- 10:03 — an engineer notices the ticket volume and begins investigating.
- 10:20 — cause identified: v4.7.0 changed the thumbnail generator to invoke an `ImageMagick` binary that is not present in the production container image.
- 10:31 — rollback to v4.6.x begins.
- 10:44 — rollback complete; uploads recover.
- 11:48 — the backlog of client-retried uploads drains; incident closed.

The change in v4.7.0 was correct in the environment its author and CI ran it in, and broken in the environment it shipped to. Production containers are built from a different Dockerfile than the one CI uses, so the artifact that passed the build was never the artifact that ran, and a missing runtime dependency was invisible until deploy. The integration suite would not have caught it either, because it mocks the thumbnail generator and so never executes the code path that shells out to the binary.

What turned a bad deploy into a two-and-a-half hour outage was the detection gap. The service handled the missing binary as an application error: it returned HTTP 200 with an error body. The upload alert measured 5xx rate, so from the alerting system's point of view the service was healthy while failing 100% of requests. Detection fell to customers, which cost 27 minutes to the first ticket and another 22 before anyone connected the tickets to an outage. Once an engineer was looking, diagnosis took 17 minutes and remediation 24, which is roughly what we would expect; the 49 minutes before that is where the time went.

Four things need to change. The production image should be built in CI and promoted as an artifact, so that the thing tested and the thing deployed are byte-identical; maintaining two Dockerfiles guarantees a class of failure that no amount of test coverage will find. At least one integration test should exercise the real thumbnail path inside the production image rather than a mock, so that missing runtime dependencies fail the build. Alerting should move from HTTP status to application-level upload success rate, with a threshold that fires within a few minutes of a sustained drop, since transport status is a proxy for health and this incident is what happens when the proxy detaches from the thing it stands for. Finally, the service should return a 5xx when it cannot complete an upload for an internal reason, both because that is the honest status code and because clients and intermediaries make retry and circuit-breaking decisions on it.

The alerting change is the one that bounds the damage of the next unrelated failure, and it should be done first.