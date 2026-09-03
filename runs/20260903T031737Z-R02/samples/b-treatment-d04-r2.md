# Incident Postmortem: Image Upload Failure (2025-07-14)

## Summary

On 2025-07-14, image uploads failed for all users for 2 hours and 36 minutes, from 09:12 to 11:48 UTC. Approximately 18,000 upload attempts failed during the window. No data was lost — every failure occurred before persistence, and the retry backlog drained cleanly once the service recovered. The cause was the deploy of `media-service` v4.7.0, which introduced a dependency on an `ImageMagick` binary that was not present in the production container image. The failure went undetected by monitoring for 51 minutes and undetected by engineers for 51 minutes beyond that, because the service returned HTTP 200 with an error body and our alerting measured HTTP status codes rather than application-level success.

## Impact

All image uploads failed from 09:14, two minutes after the deploy, until 10:44, when the rollback completed. The error rate went from a baseline of 0.2% to 100% and stayed there. Roughly 18,000 uploads failed across all customers; users saw upload failures in the client, and clients that retried automatically contributed to a backlog that took a further 64 minutes to drain after service recovery. The incident was closed at 11:48 once that backlog cleared. No data loss occurred.

## Timeline (UTC)

| Time | Event |
|---|---|
| 09:12 | `media-service` v4.7.0 deployed to production |
| 09:14 | Upload error rate rises from 0.2% to 100%. No alert fires. |
| 09:41 | First customer support ticket filed |
| 10:03 | Engineer notices ticket volume and begins investigating |
| 10:20 | Root cause identified: v4.7.0 requires an `ImageMagick` binary absent from the production container image |
| 10:31 | Rollback to previous version started |
| 10:44 | Rollback complete; uploads recover |
| 11:48 | Retried-upload backlog drains; incident closed |

## Root cause

Version 4.7.0 changed the thumbnail generator to shell out to an `ImageMagick` binary. That binary is present in the image used during CI but not in the image deployed to production, because the two are built from different Dockerfiles. When the thumbnail generator invoked the missing binary, the upload path caught the resulting error and returned an HTTP 200 response carrying an error body, so from the perspective of every layer of infrastructure between the service and the user, the request had succeeded.

## Contributing factors

Three independent gaps had to line up for this to happen, and each one is worth treating as a defect in its own right. The production container image is built from a different Dockerfile than the one CI uses, so CI cannot in principle catch a missing runtime dependency — the environment it validates is not the environment we ship. The integration test suite mocks the thumbnail generator, so even a test running against the correct image would not have exercised the code path that invokes the binary. And the alert on the upload path measured 5xx rate rather than application-level upload success, so a total outage that returned 200s was invisible to it. The first factor let the bug reach production, the second let it pass review and testing, and the third let it sit there undetected for 51 minutes until a customer told us.

Detection is the most costly of the three. The bug was found in 17 minutes once an engineer was actually looking at it; the expensive part of this incident was the 49 minutes before anyone knew there was a problem and the further 22 minutes before someone connected the ticket volume to an outage.

## Action items

| # | Action | Owner | Priority |
|---|---|---|---|
| 1 | Replace the 5xx-rate alert on the upload path with an alert on application-level upload success rate | *TBD* | High |
| 2 | Build the production container image from the same Dockerfile used in CI, or make CI test against the production image | *TBD* | High |
| 3 | Add an integration test that exercises the real thumbnail generator against the deployed image, without mocks | *TBD* | High |
| 4 | Audit other services for upload-style paths that return 200 on application-level failure, and for alerts that measure HTTP status as a proxy for success | *TBD* | Medium |
| 5 | Add a post-deploy canary check on `media-service` that verifies a real upload end to end before the deploy is marked complete | *TBD* | Medium |

## What went well

The rollback path worked exactly as intended: 13 minutes from decision to recovery, with no complications and no data loss. Client-side retry behaviour meant users who retried eventually succeeded without manual intervention on our part, and the backlog drained without needing to be replayed by hand.