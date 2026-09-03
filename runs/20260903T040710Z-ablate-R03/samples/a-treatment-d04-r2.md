# Postmortem: media-service v4.7.0 image upload outage

**Date:** 2025-07-14, 09:12–11:48 UTC (2h36m)
**Impact:** Image uploads failed for all users. Roughly 18,000 uploads failed. No data was lost; failed uploads were retried successfully after recovery.

## What happened

At 09:12 UTC we deployed media-service v4.7.0 to production. Within two minutes the upload error rate went from a baseline of 0.2% to 100%, and it stayed there for the next ninety minutes. The release had changed the thumbnail generator to shell out to an `ImageMagick` binary, and that binary is not present in the production container image, so every thumbnail generation attempt failed and every upload failed with it.

Nothing in our monitoring reacted. The upload endpoint's alert was defined on the 5xx rate, and the failing code path returned HTTP 200 with an error described in the response body, so from the alerting system's point of view the service was healthy for the entire outage. Detection came instead through customers: the first support ticket arrived at 09:41, twenty-nine minutes into the incident, and it was the accumulating ticket volume that drew an engineer's attention at 10:03. Investigation was quick once it started. By 10:20 the engineer had tied the failures to v4.7.0 and identified the missing binary; rollback began at 10:31 and completed at 10:44, at which point uploads recovered immediately. The remaining hour was spent draining the backlog of client retries, which finished at 11:48, and we closed the incident.

## Why it happened

The proximate cause is a dependency introduced in application code without a corresponding change to the runtime environment. Three conditions let that reach production and stay there.

The production container image is built from a different Dockerfile than the one CI uses. Whatever CI validated, it was not the artifact we shipped, so a missing system package in the production image was invisible to every check that ran before the deploy. This is the single most important factor: it breaks the assumption that a green build says something reliable about the thing being released.

The integration test suite mocks the thumbnail generator. The tests exercised the code that calls the generator but never the generator itself, so the suite could not have caught a failure in invoking the binary even if it had run against the correct image. The mock made the missing dependency untestable by construction.

The upload alert measured HTTP status rather than application-level success. Because the service signals failure in the response body while returning 200, our health signal was measuring something that was never going to move. Twenty-nine minutes of complete outage passed before any human knew, and another twenty-two before anyone acted, entirely because the automated path was silent.

## Remediation

The work falls into three areas, and owners and target dates are still to be assigned in the incident review.

Build production images from the Dockerfile that CI validates, or reduce the two to a single file consumed by both paths. Until the artifact under test is the artifact deployed, any other testing improvement rests on a false premise, so this should be the first item scheduled.

Replace the thumbnail generator mock in the integration suite with a test that runs the real generator inside the production image. A narrow smoke test covering the upload path end to end, run against the built image before promotion, would have failed this deploy at 09:00 rather than at 09:14.

Redefine the upload alert on application-level success rate rather than HTTP status, and audit the other service alerts for the same defect, since any endpoint that reports errors in a 200 body has the same blind spot. We should also add a post-deploy verification step that watches the application-level success rate for a few minutes after a release and rolls back automatically if it drops, which would have bounded this outage to minutes.

Separately, the ninety minutes between failure and rollback were dominated by detection rather than diagnosis. Once someone looked, the cause was found in seventeen minutes and the fix applied in eleven. The response worked; the alerting did not.