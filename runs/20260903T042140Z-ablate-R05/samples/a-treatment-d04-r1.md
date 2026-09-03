# Incident postmortem: image upload failure following media-service v4.7.0

Image uploads failed for every user for 2 hours and 36 minutes on 14 July 2025, from 09:12 to 11:48 UTC. Roughly 18,000 upload attempts failed during the window. No data was lost: uploads that failed were rejected outright rather than partially written, and the retry backlog drained cleanly once the service recovered. The cause was a deploy of `media-service` v4.7.0, whose new thumbnail generator invoked an `ImageMagick` binary that is not present in the production container image. The failure was total and immediate, but it was invisible to our alerting for 49 minutes and unattended for 51, because the service reported its failures with an HTTP 200 and an error body while our alert watched the 5xx rate.

## Timeline (UTC)

- 09:12 — `media-service` v4.7.0 deploys to production.
- 09:14 — Upload error rate rises from 0.2% to 100%. No alert fires.
- 09:41 — First customer support ticket arrives.
- 10:03 — An engineer notices the ticket volume and begins investigating.
- 10:20 — Cause identified: v4.7.0 requires an `ImageMagick` binary absent from the production image.
- 10:31 — Rollback to the previous version begins.
- 10:44 — Rollback completes; uploads recover.
- 11:48 — Backlog of retried uploads drains; incident closed.

## What happened

Version 4.7.0 rewrote thumbnail generation to shell out to `ImageMagick` rather than use the previous in-process library. That dependency was added to the Dockerfile used by CI but not to the one used to build the production image, so the binary was simply missing at runtime. Every upload reached the thumbnail step, failed to execute the binary, and returned an error to the client. Because the failure was in a required step of the upload path, there was no partial success: the feature was either working or entirely broken, and after 09:14 it was entirely broken.

Two safeguards that should have caught this before production did not. The integration test suite mocks the thumbnail generator, so the tests exercised the calling code without ever executing the binary and passed against an image that could not have run it. CI also builds from a different Dockerfile than production does, so the artifact that passed the pipeline was not the artifact that shipped. Together these meant the deploy carried no signal that anything was wrong.

## Why nobody was paged

The upload endpoint returned HTTP 200 with an application-level error in the response body. Our alert was defined on the 5xx rate, which stayed flat at its normal baseline throughout the incident, so the monitoring system's view of the service was that it remained perfectly healthy while it served zero successful uploads. Detection therefore fell to customers, who filed the first ticket 27 minutes into the outage, and to an engineer who happened to notice the ticket volume 22 minutes after that. Once someone was actually looking, diagnosis took 17 minutes and remediation another 24, which is roughly what we would expect; the loss was almost entirely in the 51 minutes before anyone knew.

## Action items

The alert is the highest-priority fix, since it is what turned a fast-to-diagnose bug into a two-and-a-half-hour outage. We should alert on the application-level upload success rate rather than on HTTP status, and separately treat the 200-with-error-body response as a defect in its own right: a server-side failure to process an upload should return a 5xx, both so that generic monitoring sees it and so that clients retry with correct backoff semantics.

Next, the two Dockerfiles need to become one. CI must build the image that ships, and the production deploy must consume that artifact rather than rebuild from a separate definition; until they are unified, any dependency change can diverge the same way this one did.

The mocked thumbnail generator should be replaced in at least one integration test by a real invocation running inside the production image, so that a missing binary fails the pipeline rather than the users. Finally, a post-deploy smoke test that performs one genuine end-to-end upload and asserts on the response body would have caught this within a minute or two of 09:12, and is worth adding independently of the other three.