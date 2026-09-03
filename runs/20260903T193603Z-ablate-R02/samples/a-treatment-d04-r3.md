# Postmortem: image upload failure, 2025-07-14

## Summary

A deploy of `media-service` v4.7.0 at 09:12 UTC broke image uploads for all users. The new version's thumbnail generator shelled out to an `ImageMagick` binary that was not present in the production container image, so every upload failed. Because the service returned HTTP 200 with an error body, the 5xx-rate alert never fired, and the failure went unnoticed for 49 minutes until support ticket volume drew an engineer's attention. A rollback restored uploads at 10:44. The retry backlog drained by 11:48, when the incident was closed.

Total incident duration was 2h36m. Users were unable to upload for 1h30m of that; the remainder was backlog recovery. Roughly 18,000 uploads failed. All were retried successfully and no data was lost.

## Timeline (UTC)

- **09:12** — v4.7.0 of `media-service` deploys to production.
- **09:14** — upload error rate rises from 0.2% to 100%. No alert fires: the alert is defined on 5xx rate, and the failing requests return 200 with an error body.
- **09:41** — first customer support ticket arrives.
- **10:03** — an engineer notices the ticket volume and begins investigating.
- **10:20** — cause identified: v4.7.0 changed the thumbnail generator to require an `ImageMagick` binary absent from the production container image.
- **10:31** — rollback to the previous version begins.
- **10:44** — rollback complete; uploads recover.
- **11:48** — backlog of retried uploads drains. Incident closed.

## Root cause

v4.7.0 introduced a dependency on an `ImageMagick` binary at runtime. The production container image does not contain that binary, so the thumbnail generation step failed on every upload. The failure was total rather than partial because thumbnail generation is on the critical path for all image uploads.

## Contributing factors

Three separate gaps let this reach production and stay there.

The production container image is built from a different Dockerfile than the one CI uses. This means CI cannot tell you whether a new runtime dependency exists in the artifact that actually ships; a change can pass every check in a container that does not resemble production.

The integration test suite mocks the thumbnail generator. The one layer of testing that might have exercised the real binary substituted a stub for it, so the missing dependency was invisible to the tests as well as to the build.

The upload alert measured HTTP status rather than application-level success. The service was returning 200 for requests it had failed to fulfil, which is a defect in its own right, but the consequence here was that a 100% failure rate looked healthy to monitoring. Detection fell back on customers filing tickets, which added roughly 49 minutes to the incident before anyone was looking at it.

Once an engineer was engaged, the response was fast: 17 minutes to diagnosis, 11 more to start the rollback, 13 to complete it. The time cost of this incident was almost entirely in detection, not in response.

## Action items

The following are proposed; owners and dates need to be assigned by the service team.

1. Build the production image from the same Dockerfile CI tests against, or make CI test the production artifact directly. This is the fix that would have caught the defect before deploy.
2. Replace the mocked thumbnail generator in at least one integration test path with the real binary, so runtime dependencies of that component are exercised.
3. Alert on application-level upload success rate rather than HTTP status. A sustained drop in successful uploads should page regardless of the status codes being returned.
4. Correct `media-service` to return a 5xx status when an upload fails. The 200-with-error-body behaviour misleads clients and monitoring alike, and other alerts likely depend on the same assumption.
5. Review whether other services return 200 on failure, since the alerting gap generalises beyond this one endpoint.

## What went well

The rollback was clean and uploads recovered immediately once it completed. Failed uploads were retried rather than dropped, which is why an outage affecting 18,000 uploads produced no data loss.