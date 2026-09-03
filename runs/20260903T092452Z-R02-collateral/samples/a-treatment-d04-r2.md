# Incident postmortem: image upload failure following media-service v4.7.0

**Date:** 2025-07-14, 09:12–11:48 UTC (2h36m)
**Status:** Resolved, no data loss

## Summary

A deploy of `media-service` v4.7.0 introduced a dependency on an `ImageMagick` binary that is not present in the production container image. Thumbnail generation failed for every upload from the moment the deploy landed. Because the service caught the failure and returned HTTP 200 with an error body, the 5xx-rate alert never fired, and the outage was detected only when support ticket volume drew an engineer's attention 49 minutes later. A rollback to the previous version restored uploads at 10:44; the queue of client-retried uploads drained by 11:48.

## Impact

Image uploads failed for all users for 90 minutes, from 09:14 to 10:44. Roughly 18,000 upload attempts failed during that window. No data was lost: uploads that failed were rejected outright rather than partially written, and the clients that retried succeeded once the rollback completed. The remaining hour of the incident window was backlog drain, during which uploads succeeded but latency was elevated.

## Timeline

| Time (UTC) | Elapsed | Event |
|---|---|---|
| 09:12 | 0m | `media-service` v4.7.0 deployed to production |
| 09:14 | +2m | Upload error rate rises from 0.2% to 100%. No alert fires |
| 09:41 | +29m | First customer support ticket filed |
| 10:03 | +51m | Engineer notices ticket volume and begins investigating |
| 10:20 | +1h08m | Cause identified: v4.7.0 requires an `ImageMagick` binary absent from the production image |
| 10:31 | +1h19m | Rollback started |
| 10:44 | +1h32m | Rollback complete, uploads recover |
| 11:48 | +2h36m | Retried-upload backlog drains, incident closed |

## Root cause

v4.7.0 reworked the thumbnail generator to shell out to `ImageMagick` rather than use the previous in-process library. The binary is installed in the image CI builds, but production containers are built from a separate Dockerfile that does not install it, so the call failed on the first upload after the deploy and on every upload thereafter. The generator's failure path returned an error body inside a 200 response, which meant the upload endpoint reported success at the HTTP layer while failing at the application layer for every request.

## Contributing factors

Three conditions had to hold at once for a missing binary to become a two-hour outage, and each is independently worth fixing.

- **Divergent build definitions.** The production container image is built from a different Dockerfile than the one CI uses. Nothing in the pipeline exercises the artifact that actually ships, so a dependency added to the CI image and not the production image passes every gate.
- **Mocked integration tests.** The integration suite mocks the thumbnail generator, so no test in the pipeline invokes the real binary. The suite would have passed identically whether or not `ImageMagick` existed anywhere.
- **Alerting on transport status rather than outcome.** The upload alert measured 5xx rate. A total application-level failure that returns 200 is invisible to that signal, which is why a 100% error rate ran for 49 minutes and was surfaced by customers rather than by monitoring.

Detection is the largest of the three by time cost. Cause identification and rollback took 41 minutes once someone was looking, which is reasonable; the preceding 49 minutes of undetected failure is the part that a working alert would have removed almost entirely.

## Action items

Owners and target dates are not assigned below, since that allocation belongs with the teams that hold these systems.

1. Alert on application-level upload success rate, not HTTP status, and page on a sustained drop. This is the single change that would have cut the incident to roughly its last 40 minutes.
2. Build production images from the same Dockerfile CI uses, or fail the pipeline when the two diverge. A shared base image with a single dependency manifest is the more durable form of this fix.
3. Add at least one integration test that runs the real thumbnail generator against the production image, with no mock in the path.
4. Correct the error-handling contract in `media-service` so that a failed upload returns a 5xx. The mismatch between response code and outcome hid this failure and will hide the next one.
5. Add a post-deploy check that compares upload success rate against the pre-deploy baseline and blocks or reverts the rollout on a significant regression. A two-minute detection window would have made this a non-incident.