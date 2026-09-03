# Incident postmortem: media-service upload failure

**Date:** 2025-07-14, 09:12–11:48 UTC (2h36m)
**Impact:** Image uploads failed for all users. Roughly 18,000 uploads failed. No data was lost; failed uploads were retried and the backlog drained by 11:48.

## Summary

A deploy of `media-service` v4.7.0 at 09:12 changed the thumbnail generator to invoke an `ImageMagick` binary that is not present in the production container image. Every upload that reached thumbnail generation failed from 09:14 onward, taking the error rate from a baseline of 0.2% to 100%. Because the service returned HTTP 200 with an error body rather than a 5xx, the alert on 5xx rate never fired, and no automated signal of the outage existed. The first indication was a customer support ticket at 09:41; an engineer noticed the ticket volume at 10:03 and began investigating, identifying the missing binary at 10:20. A rollback started at 10:31 and completed at 10:44, at which point uploads recovered. The incident was closed at 11:48 once the retry backlog had drained.

The failure was total and lasted 91 minutes before recovery, but the more significant number is 111 minutes: the time from the first failed upload to the moment a human began investigating. During that entire window the system reported itself healthy.

## Timeline (UTC)

- **09:12** — `media-service` v4.7.0 deployed to production.
- **09:14** — Upload error rate rises from 0.2% to 100%. No alert fires; the alert condition is 5xx rate, and the service is returning 200 with an error body.
- **09:41** — First customer support ticket filed (27 minutes into the outage).
- **10:03** — Engineer notices the volume of incoming tickets and begins investigating.
- **10:20** — Cause identified: v4.7.0's thumbnail generator requires an `ImageMagick` binary absent from the production container image.
- **10:31** — Rollback to the previous version started.
- **10:44** — Rollback complete. Uploads recover.
- **11:48** — Backlog of retried uploads drains. Incident closed.

## Root cause

v4.7.0 introduced a dependency on an external `ImageMagick` binary in the thumbnail generation path. The production container image does not include that binary, so every invocation failed at the point of shelling out. The upload handler treated thumbnail generation failure as a non-fatal condition at the transport layer and returned HTTP 200 with an error payload, which meant the failure was invisible to any monitor keyed on status code while being fatal to the user's upload.

## Contributing factors

Three conditions had to hold simultaneously for a missing binary to become a two-and-a-half-hour total outage, and each is independently worth fixing.

The production container image is built from a different Dockerfile than the one CI uses. A new binary dependency added to the CI image therefore satisfies the test environment without ever reaching production, and no stage of the pipeline compares the two. This is the defect that let the bad artifact ship; the divergence is not detectable from within either build in isolation.

The integration test suite mocks the thumbnail generator. The test that would have exercised the new code path against a real binary instead exercised a stub, so the suite passed on an image where the feature could not run. Mocking at this boundary means the suite cannot distinguish "thumbnail generation works" from "thumbnail generation is called."

The upload alert measured HTTP status rather than application-level success. A 100% application failure rate produced a 0% 5xx rate, so the alert was not merely slow, it was structurally incapable of firing for this class of failure. Detection fell back to customer support tickets, which added 51 minutes before the first report and 111 minutes before investigation began.

## Action items

The following are proposed rather than agreed; owners and target dates need to be assigned by the media-service team.

1. **Build the production image from the CI Dockerfile,** or fail the pipeline when the two diverge. A single artifact promoted from CI to production removes the class of failure entirely and is preferable to a comparison check.
2. **Alert on application-level upload success rate,** not on 5xx rate. The alert should fire on a sustained drop in successful uploads regardless of status code, with a threshold tight enough to catch this outage within minutes of 09:14.
3. **Return a 5xx status when an upload fails.** Returning 200 with an error body misrepresents the outcome to clients, retry logic, and monitoring alike; the status code should reflect whether the upload succeeded.
4. **Add an integration test that exercises thumbnail generation unmocked against the production image.** The mock should be reserved for tests where thumbnail generation is incidental, not for the tests that cover it.
5. **Add a smoke test to the deploy pipeline** that performs a real upload against the newly deployed version and rolls back automatically on failure. Any of the above would have caught this deploy; a post-deploy smoke test catches the next dependency that slips through all of them.

## What went well

Once investigation began, diagnosis took 17 minutes and rollback took 13. The retry path preserved every failed upload, so an outage affecting 100% of users for 91 minutes produced no data loss.