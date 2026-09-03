# Incident Postmortem: Image Upload Failure

**Date:** 2025-07-14
**Duration:** 09:12–11:48 UTC (2h 36m)
**Severity:** Full outage of a core feature
**Status:** Resolved

## Impact

Image uploads failed for all users for the duration of the incident — roughly 18,000 failed uploads. No data was lost; failed uploads were retried successfully once the service recovered.

## Timeline (UTC)

| Time | Event |
|---|---|
| 09:12 | `media-service` v4.7.0 deployed to production |
| 09:14 | Upload error rate rises from 0.2% to 100%. No alert fires. |
| 09:41 | First customer support ticket |
| 10:03 | Engineer notices ticket volume, begins investigating |
| 10:20 | Root cause identified: v4.7.0 requires an `ImageMagick` binary absent from the production container image |
| 10:31 | Rollback started |
| 10:44 | Rollback complete; uploads recover |
| 11:48 | Retry backlog drains; incident closed |

## Root cause

v4.7.0 changed the thumbnail generator to shell out to an `ImageMagick` binary. That binary is not present in the production container image, so every thumbnail generation attempt failed, and with it every upload.

The failure was invisible to monitoring because the service returned HTTP 200 with an error body rather than a 5xx. The upload alert measured 5xx rate, so it never fired.

## Contributing factors

**Production and CI build from different Dockerfiles.** The image CI tests against is not the image that runs in production, so a missing runtime dependency in the production image cannot be caught by any CI run. This is what allowed the change to ship at all.

**Integration tests mock the thumbnail generator.** The test suite exercises the calling code but never the generator's actual dependencies, so no test could have detected the missing binary even with a correct Dockerfile.

**The alert measured transport, not outcome.** Alerting on HTTP status assumes failures surface as 5xx. Here they did not, so a 100% failure rate produced no signal. Detection fell to customer support tickets — 27 minutes to the first ticket, 51 minutes before an engineer picked it up. Roughly two thirds of total incident duration was detection time, not repair time.

## What went well

Once investigation started, diagnosis took 17 minutes and rollback completed 24 minutes after that. The rollback path itself worked cleanly and no data was lost.

## Action items

| Action | Rationale |
|---|---|
| Build production images from the CI Dockerfile, or make them the same artifact | Removes the class of bug where prod has dependencies CI does not |
| Alert on application-level upload success rate, not 5xx rate | This incident produced zero alerting signal at 100% failure |
| Add at least one integration test that runs the real thumbnail generator against the production image | Mocks cannot detect missing runtime dependencies |
| Audit other alerts for the same status-vs-outcome assumption | The `media-service` alert is unlikely to be the only one |
| Add a post-deploy check on key success metrics with automatic rollback or page | 09:14 to 10:03 was silent; deploys should watch themselves |