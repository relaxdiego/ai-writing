# Incident postmortem: image upload failure after media-service v4.7.0

**Date:** 2025-07-14
**Duration:** 09:12–11:48 UTC (2h36m)
**Impact:** Image uploads failed for all users. Approximately 18,000 uploads failed. No data was lost.
**Severity:** Full outage of a single user-facing feature.

## Summary

A routine deploy of `media-service` v4.7.0 introduced a dependency on the `ImageMagick` binary in the thumbnail generation path, and that binary is not present in the production container image. Every upload that reached thumbnail generation failed from 09:14 onward. The failure was invisible to our monitoring because the service caught the error and returned HTTP 200 with an error body, while the paging alert was defined on 5xx rate; nothing fired, and the outage was eventually surfaced by customers rather than by us. Detection took 51 minutes from the first support ticket and 89 minutes from the start of the failure, which is the largest single contributor to the length of this incident. Once an engineer began investigating, diagnosis took 17 minutes and rollback restored service 24 minutes after that.

## Timeline (UTC)

| Time | Event |
|---|---|
| 09:12 | `media-service` v4.7.0 deployed to production. |
| 09:14 | Upload error rate rises from 0.2% to 100%. No alert fires: the alert measures 5xx rate, and the service returns 200 with an error body. |
| 09:41 | First customer support ticket filed. |
| 10:03 | An engineer notices the ticket volume and begins investigating. |
| 10:20 | Cause identified: v4.7.0 changed the thumbnail generator to shell out to `ImageMagick`, which is absent from the production container image. |
| 10:31 | Rollback to the previous version begins. |
| 10:44 | Rollback complete; uploads recover. |
| 11:48 | Backlog of client-retried uploads drains. Incident closed. |

## Root cause

Version 4.7.0 rewrote thumbnail generation to invoke the `ImageMagick` binary as an external process. The change passed review and passed CI, because the production container image is built from a different Dockerfile than the one CI builds and exercises, and because the integration test suite mocks the thumbnail generator rather than running it. Neither gate could have caught a missing runtime binary: one was testing a different image, and the other never executed the code that needed it. The dependency was therefore satisfied everywhere the change was verified and unsatisfied in the only environment that mattered.

## Contributing factors

The two-Dockerfile split is the underlying structural problem. As long as CI validates an artifact that is not the artifact we ship, any divergence between them is invisible until deploy, and this class of failure will recur with a different missing dependency. The mocked integration tests compound it by removing the last opportunity to notice; a test that exercised the real generator against the real image would have failed loudly in CI even with the Dockerfile split in place.

The alerting gap turned a fast failure into a slow one. Because the alert measured transport-level status rather than application-level success, a service that was failing 100% of its core operation looked healthy on every dashboard we page on. The 200-with-error-body response pattern is not itself wrong, but it means HTTP status carries no signal about whether uploads are working, and our monitoring had not been updated to reflect that. Customers were the detection mechanism, and even then the signal took 22 minutes to accumulate into enough tickets for someone to notice, since ticket volume is not itself an alerting input.

## What went well

Once investigation started, the path from symptom to cause to rollback was quick and unambiguous — 17 minutes to diagnose and 13 minutes to complete the rollback, with no false starts. The service degraded cleanly: uploads failed rather than partially succeeding, so no images were stored in a corrupt or half-processed state and no data was lost. Client-side retry behavior meant most affected uploads completed on their own once the rollback landed, without manual intervention or a backfill.

## Action items

1. **Build production and CI images from a single Dockerfile.** Eliminate the divergence rather than trying to keep two files in sync; the artifact CI tests must be the artifact we deploy.
2. **Run thumbnail generation unmocked in at least one integration test**, against the real container image, so that missing runtime dependencies fail the build.
3. **Alert on application-level upload success rate**, not 5xx rate, for `media-service`. The threshold should page well below the 100% failure seen here — a sustained drop of a few percent is already an incident.
4. **Audit other services for the same alerting gap**, specifically any endpoint that returns 200 with an error body. Wherever HTTP status does not reflect operational success, the alert needs a different input.
5. **Add support ticket volume as a monitored signal.** It was the only working detector in this incident and it was read by a human who happened to look.
6. **Review deploy-time verification for `media-service`**: a post-deploy smoke test that uploads one image would have caught this within two minutes of 09:12.

Owners and target dates are not assigned here and should be filled in at the review meeting.