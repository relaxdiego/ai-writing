# Incident Postmortem: Image Upload Failure (media-service v4.7.0)

**Date:** 2025-07-14
**Duration:** 09:12–11:48 UTC (2h 36m)
**Severity:** Full feature outage, all users
**Status:** Resolved

## Summary

A routine deploy of `media-service` v4.7.0 introduced a dependency on the `ImageMagick` binary, which is not present in the production container image. Every image upload failed from 09:14 onward, affecting roughly 18,000 upload attempts across all users. No data was lost; failed uploads returned an error to the client and were retried after recovery. The outage ran undetected by monitoring for its entire duration and was surfaced only by customer support volume, because the failing code path returned HTTP 200 with an error body while our alerting measured 5xx rate.

## Impact

All image uploads failed for 2 hours and 36 minutes, with the user-visible failure window running 09:14 to 10:44 and the remaining hour spent draining the backlog of client retries. Approximately 18,000 upload attempts failed during that window. Because the service rejected the uploads rather than partially processing them, no images were corrupted and no stored data was lost — users who retried after 10:44 succeeded, and the queued retries drained on their own by 11:48.

## Timeline (UTC)

| Time | Event |
|---|---|
| 09:12 | `media-service` v4.7.0 deploys to production |
| 09:14 | Upload error rate rises from 0.2% to 100%; no alert fires |
| 09:41 | First customer support ticket filed |
| 10:03 | Engineer notices ticket volume and begins investigating |
| 10:20 | Root cause identified: v4.7.0 requires an `ImageMagick` binary absent from the production image |
| 10:31 | Rollback to v4.6.x begins |
| 10:44 | Rollback complete; uploads recover |
| 11:48 | Retry backlog drains; incident closed |

## Root cause

Version 4.7.0 changed the thumbnail generator to shell out to `ImageMagick`. The production container image does not include that binary, so every invocation of the generator failed at runtime. The upload handler caught the failure and returned a 200 response carrying an application-level error, which meant the request completed successfully as far as our HTTP-layer instrumentation was concerned even though the user's upload had not.

Three gaps let the change reach production and stay there. The production container is built from a different Dockerfile than the one CI uses, so the CI image contained `ImageMagick` and the production image did not — the divergence meant a green build carried no information about whether the binary would exist at runtime. The integration test suite mocks the thumbnail generator, so no test exercised the real binary path and the missing dependency produced no signal at any stage of the pipeline. Finally, the upload alert was defined on HTTP 5xx rate rather than on application-level upload success, so a 100% functional failure rate looked identical to healthy traffic on our dashboards.

## Detection and response

Detection took 49 minutes and came from customers rather than monitoring: the first support ticket arrived at 09:41, and it took until 10:03 for ticket volume to be noticed and an investigation to start. Once an engineer was engaged, diagnosis was fast — 17 minutes from investigation to identified root cause, and another 24 minutes to a completed rollback. The response phase worked roughly as we would want it to; the detection phase did not work at all, and the bulk of user-visible impact is attributable to the 49 minutes before anyone knew there was an incident.

## Contributing factors

- **Dockerfile divergence between CI and production.** The two images are built from separate files with no mechanism enforcing that runtime dependencies stay in sync, so CI cannot validate what production will actually run.
- **Mocked integration tests.** Mocking the thumbnail generator removes the one test that would have caught a missing system binary, and the mock made the suite pass with more confidence than the code deserved.
- **Status-code-based alerting.** Measuring HTTP status rather than application-level success meant the alert was blind to a failure mode where the service reports success and delivers none.

## Action items

| # | Action | Owner | Priority |
|---|---|---|---|
| 1 | Alert on application-level upload success rate, not 5xx rate; page on sustained failure above 5% | Platform | P0 |
| 2 | Build production and CI images from a single Dockerfile, or add a check that fails the build on dependency divergence | Infra | P0 |
| 3 | Add an integration test that exercises the real thumbnail generator against the production image | Media | P1 |
| 4 | Return a non-2xx status from the upload handler when processing fails, so HTTP-layer monitoring reflects reality | Media | P1 |
| 5 | Audit remaining alerts for the same status-vs-outcome mismatch on other user-facing paths | Platform | P2 |
| 6 | Add a support-ticket-volume signal that notifies the on-call engineer, as a backstop for monitoring gaps | Support / Platform | P2 |

## What went well

The rollback path was clean and fast — once the cause was understood, reverting took 13 minutes and uploads recovered immediately, with no manual data repair needed. The failure was also fail-closed: the service rejected uploads outright rather than storing images without thumbnails or writing partial records, which is why an outage of this length produced no data loss and required no cleanup beyond letting client retries drain.