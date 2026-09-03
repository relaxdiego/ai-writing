# Incident postmortem: media-service upload failure

**Date:** 2025-07-14, 09:12–11:48 UTC (2h 36m)
**Impact:** All image uploads failed for all users. Roughly 18,000 uploads were rejected. No data was lost, and the backlog of client retries drained successfully once the service recovered.

## Summary

Version 4.7.0 of `media-service` changed the thumbnail generator to shell out to an `ImageMagick` binary. That binary is not present in the production container image, so every upload failed at the thumbnail step from the moment the deploy landed. The service caught the failure and returned HTTP 200 with an error body, which meant the upload alert, measured on 5xx rate, never fired. The failure was discovered 49 minutes later through customer support ticket volume, and resolved by rolling back to 4.6.x.

## Timeline (UTC)

- 09:12 — `media-service` v4.7.0 deploys to production.
- 09:14 — Upload error rate rises from 0.2% to 100%. No alert fires.
- 09:41 — First customer support ticket arrives.
- 10:03 — An engineer notices the ticket volume and begins investigating.
- 10:20 — v4.7.0 is identified as the cause: the new thumbnail generator requires an `ImageMagick` binary absent from the production image.
- 10:31 — Rollback begins.
- 10:44 — Rollback completes; uploads recover.
- 11:48 — Retry backlog drains. Incident closed.

## What happened

The thumbnail generator in 4.7.0 was rewritten to invoke `ImageMagick` as an external process rather than doing the work in-process. The change was correct against the environment the tests ran in and incorrect against the environment the code shipped to, because the production container image is built from a different Dockerfile than the one CI uses. Nothing in the pipeline compares the two, so a dependency added to the CI image satisfies every check while the production image goes out without it. The integration suite did not catch the gap either: it mocks the thumbnail generator, so the code path that shells out to the binary is never executed against a real image at any point before production.

The outage lasted 90 minutes from first failure to recovery, and 49 of those minutes were spent before anyone knew there was an incident. That detection gap is the largest single component of the impact, and it is the direct result of the upload alert measuring HTTP status rather than application-level success. The service was behaving as designed when it caught the thumbnail error and returned a 200 with an error body in it, but the alert had no way to see the difference between that and a successful upload. From the monitoring system's point of view the service was healthy throughout. Once an engineer was actually looking, diagnosis took 17 minutes and the rollback took 13, which is a reasonable response to an incident that had been running unobserved for the better part of an hour.

## Contributing factors

Three separate gaps had to line up, and each of them independently would have caught this one. The production Dockerfile diverges from the CI Dockerfile with no mechanism to detect drift between them, so the environment that was tested was not the environment that ran. The integration test suite mocks the thumbnail generator, so no test exercises the real binary invocation. And the alerting for uploads is defined on transport-layer status codes, so an application-level failure that returns 200 is invisible to it.

## Action items

1. Build production and CI containers from the same Dockerfile, or add a pipeline check that fails when the two diverge. This is the fix that would have prevented the incident outright.
2. Change the upload alert to fire on application-level upload success rate rather than 5xx rate, with a threshold that would have triggered within a few minutes of 09:14.
3. Add at least one integration test that exercises the thumbnail generator unmocked, against the production image, as part of the deploy pipeline.
4. Audit the remaining alerts on `media-service` for the same status-code-versus-outcome mismatch. The upload alert is unlikely to be the only one defined this way.
5. Add a smoke test to the deploy that performs a real upload against the newly deployed version before the deploy is marked complete.