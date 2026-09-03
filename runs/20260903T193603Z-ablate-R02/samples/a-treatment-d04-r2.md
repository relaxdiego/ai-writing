# Postmortem: image upload outage, 14 July 2025

## Summary

Between 09:12 and 11:48 UTC on 14 July 2025, a total of 2 hours 36 minutes, image uploads failed for every user of the platform. Roughly 18,000 upload attempts failed. No data was lost: uploads that failed were rejected outright rather than partially written, and the client retry queue drained successfully once service was restored.

The cause was the deploy of `media-service` v4.7.0, which changed the thumbnail generator to invoke an `ImageMagick` binary that is not present in the production container image. Every upload reached the thumbnail step and failed there.

The failure was not detected by monitoring. It was detected by customers, and it took 49 minutes from the onset of the failure before an engineer began investigating.

## Timeline (UTC)

- **09:12** — `media-service` v4.7.0 deployed.
- **09:14** — Upload error rate rises from 0.2% to 100%. No alert fires: the alert is defined on 5xx rate, and the failing requests return HTTP 200 with an error body.
- **09:41** — First customer support ticket arrives, 27 minutes after the failure began.
- **10:03** — An engineer notices the rising ticket volume and starts investigating.
- **10:20** — Cause identified: v4.7.0 requires `ImageMagick`, which is absent from the production image.
- **10:31** — Rollback to the previous version begins.
- **10:44** — Rollback complete; uploads recover.
- **11:48** — Backlog of retried uploads drains. Incident closed.

## What happened

The thumbnail generator in v4.7.0 was rewritten to shell out to `ImageMagick` rather than use the previous in-process library. The production container image does not contain that binary, so the subprocess invocation failed on every upload. The service caught the failure, returned an error body, and returned it with a 200 status code.

Two things kept this from being caught before the deploy. The production container image is built from a different Dockerfile than the one CI uses, so nothing in the pipeline ever exercised the artefact that actually runs in production; CI's image happened to include `ImageMagick`. And the integration suite mocks the thumbnail generator, so no test in any environment ran the new code path against a real binary. A dependency that existed only in the test environment was therefore invisible twice over.

## Why it wasn't detected

The upload alert measured HTTP status rather than application-level success. Because the service answered 200 on a failed upload, the alert's view of the system was that nothing had changed. This is the more serious of the two findings: the missing binary was a one-off mistake, but an alert that cannot see a total outage of its own service will fail to see the next one too, whatever its cause.

The 22 minutes between the first support ticket and the start of investigation are a secondary concern. Support ticket volume is not currently a monitored signal, and the rise was noticed incidentally.

## Corrective actions

Owners and target dates are not yet assigned; that should happen at the review meeting before this document is circulated further.

1. Change the upload alert to fire on application-level upload success rate rather than HTTP status. Audit the remaining service alerts for the same defect, since the 200-on-error pattern is unlikely to be unique to this endpoint.
2. Build the production image from the same Dockerfile CI uses, or, if the two must diverge, have CI run its test suite against the production artefact rather than a separately built one.
3. Add at least one integration test that exercises the real thumbnail generator against the production image, without mocks, so that a missing runtime dependency fails the build.
4. Add a check to the deploy pipeline that compares the declared runtime dependencies of a release against the contents of the image it will run in.
5. Route support ticket volume spikes to the on-call engineer as a paging signal. This is a backstop, not a substitute for item 1.

Items 1 and 2 are the ones that would have prevented or sharply shortened this incident. Item 3 would have prevented it at the cost of a slower test suite. Items 4 and 5 are defence in depth and can follow.