# Incident Postmortem: `media-service` v4.7.0 Upload Failure

**Date:** 2025-07-14
**Duration:** 09:12–11:48 UTC (2h 36m)
**Impact:** Image uploads failed for all users. Roughly 18,000 uploads failed. No data loss.

## Summary

A deploy of `media-service` v4.7.0 introduced a dependency on an `ImageMagick` binary that was not present in the production container image. Every upload failed at thumbnail generation. Because the service returned HTTP 200 with an error body, no alert fired, and the failure was discovered only after customers reported it — 49 minutes into the outage. A rollback restored service at 10:44; the retry backlog drained by 11:48.

## Timeline (UTC)

| Time | Event |
|---|---|
| 09:12 | `media-service` v4.7.0 deployed |
| 09:14 | Upload error rate rises from 0.2% to 100%. No alert fires. |
| 09:41 | First customer support ticket |
| 10:03 | Engineer notices ticket volume, begins investigating |
| 10:20 | Root cause identified: v4.7.0 requires `ImageMagick`, absent from the production image |
| 10:31 | Rollback started |
| 10:44 | Rollback complete; uploads recover |
| 11:48 | Retried-upload backlog drains; incident closed |

Time to detection: 49 minutes. Time to mitigation: 1h 32m.

## Root cause

v4.7.0 changed the thumbnail generator to shell out to an `ImageMagick` binary. The production container image does not include that binary, so thumbnail generation failed on every upload immediately after deploy.

## Contributing factors

**The production container image is built from a different Dockerfile than the one used in CI.** CI validated an image that was not the image shipped. A missing binary in production was therefore invisible to every test that ran before the deploy.

**The integration test suite mocks the thumbnail generator.** The one test layer that could have exercised the real binary substituted a mock, so the new dependency was never invoked against a real filesystem in any pipeline stage.

**The alert measured HTTP status rather than application-level success.** The service returned 200 with an error body on failure, so a total outage produced a clean 5xx rate. The alert was structurally incapable of firing for this class of failure — a 100% failure rate went unnoticed for 49 minutes and was ultimately surfaced by customers.

## What went well

The rollback itself was fast: 11 minutes from decision to recovery. Once an engineer was looking at the problem, root cause took 17 minutes to identify.

## Action items

| Action | Rationale |
|---|---|
| Build the production image from the same Dockerfile CI tests against, or test the exact artifact that ships | Removes the CI/production divergence that let the missing binary through |
| Alert on application-level upload success rate, not HTTP status | The current alert cannot detect 200-with-error-body failures |
| Run at least one integration test against the real thumbnail generator, unmocked, in the shipped image | Catches missing runtime dependencies before deploy |
| Add a post-deploy smoke test that performs a real upload end to end | Bounds detection time for deploy-induced total failures |

## Open questions

- Were the 18,000 failed uploads retried successfully by clients, or is user-visible content still missing?
- Are other services in the fleet built from CI-divergent Dockerfiles, or is `media-service` unique?
- Do other alerts in this service measure HTTP status where application-level success is the real signal?