# Incident postmortem: image upload failure, 2025-07-14

## Summary

Between 09:12 and 11:48 UTC on 14 July 2025, a total of 2 hours and 36 minutes, image uploads failed for all users of the platform. Roughly 18,000 upload attempts failed during the window. No data was lost: uploads that failed were rejected outright rather than partially written, and the retry backlog drained cleanly once the service recovered. The cause was a deploy of `media-service` v4.7.0, which changed the thumbnail generator to invoke an `ImageMagick` binary that is not present in the production container image. Because the service caught the resulting failure and returned HTTP 200 with an error body, no alert fired, and the outage was found only after support ticket volume rose high enough for an engineer to notice it 51 minutes into the incident.

## Timeline

All times UTC.

- **09:12** — `media-service` v4.7.0 deployed to production.
- **09:14** — Upload error rate rises from 0.2% to 100%. No alert fires; the alert is defined on 5xx rate, and the service is returning 200 responses carrying an error body.
- **09:41** — First customer support ticket arrives.
- **10:03** — An engineer notices the ticket volume and begins investigating.
- **10:20** — Cause identified: v4.7.0 changed the thumbnail generator to require an `ImageMagick` binary absent from the production container image.
- **10:31** — Rollback to the prior version begins.
- **10:44** — Rollback complete; uploads recover.
- **11:48** — Backlog of retried uploads drains; incident closed.

## What happened

The thumbnail generation path in v4.7.0 was reworked to shell out to `ImageMagick` rather than use the previous in-process library. That dependency was added to the CI build environment but not to the image that actually runs in production, so every upload reached the thumbnail step, failed to find the binary, and aborted. The failure was total and immediate: from the first request served by the new version, no upload could complete.

Detection failed at two levels. The application caught the generator error and returned a 200 response with a failure described in the body, which meant the outage was invisible to alerting defined on HTTP status codes; the error rate our dashboards reported stayed flat while the real success rate sat at zero. Discovery then depended on a human noticing an unusual pattern in the support queue, which took a further 22 minutes after the first ticket. Once an engineer was looking at the problem, diagnosis and remediation were fast: 17 minutes to identify the cause, 11 minutes to start the rollback, and 13 minutes for it to complete.

## Contributing factors

The production container image is built from a different Dockerfile than the one CI uses. A dependency added for the new generator was therefore satisfied in every environment that ran the tests and missing in the only environment that mattered. This divergence had existed for some time and had not previously caused a visible failure, which is why it survived review.

The integration test suite mocks the thumbnail generator. The suite exercised the code path that calls the generator but never the generator itself, so a change to how the generator is invoked, and to what it depends on, could not fail a test. The mock was introduced to keep the suite fast, and the cost of that choice was paid here.

The upload alert measured HTTP status rather than application-level success. Returning 200 with an error body is a defensible API design in some contexts, but it makes status-code alerting meaningless, and the alert had been written without that in mind. This is the factor that turned a bad deploy into a two-and-a-half-hour outage rather than a five-minute one.

## Action items

We will alert on application-level upload success rate rather than HTTP status, with a page threshold that would have fired within two minutes of 09:14. Alongside that, we will audit remaining alerts on services that return 200 for application failures, since the same blind spot likely exists elsewhere.

We will eliminate the Dockerfile divergence so that CI builds and tests the same image that ships to production. Until that is complete, we will add a startup check to `media-service` that verifies its external binary dependencies and refuses to start if any are missing, which would have failed the deploy at 09:12 rather than silently degrading it.

We will replace the mocked thumbnail generator in the integration suite with the real one running against the production image. This is slower, and we accept the added suite runtime as the price of testing the dependency surface that broke here.