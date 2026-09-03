# Postmortem: image upload failure, 2025-07-14

## Summary

Between 09:12 and 11:48 UTC on 14 July 2025, image uploads failed for every user of the service. The `media-service` v4.7.0 release changed the thumbnail generator to shell out to an `ImageMagick` binary that is not present in the production container image, so every upload failed at the thumbnailing step. Roughly 18,000 uploads failed over the course of the incident. No data was lost: uploads that failed were rejected outright rather than partially written, and the clients that retried succeeded once the rollback was in place.

The failure was total from 09:14, but nothing in our monitoring reported it. The upload endpoint returned HTTP 200 with an error body, and our alerting measured 5xx rate, so the alert never fired. The outage was discovered 49 minutes later through customer support tickets and was not escalated to an engineer for another 22 minutes after that. Once someone was actually looking at it, diagnosis took 17 minutes and recovery took a further 24.

## Timeline (UTC)

- **09:12** — `media-service` v4.7.0 deployed to production.
- **09:14** — Upload error rate rises from 0.2% to 100%. No alert fires.
- **09:41** — First customer support ticket arrives.
- **10:03** — An engineer notices the volume of tickets and begins investigating.
- **10:20** — Cause identified: v4.7.0 requires an `ImageMagick` binary absent from the production container image.
- **10:31** — Rollback to the previous version begins.
- **10:44** — Rollback complete. Uploads recover.
- **11:48** — Backlog of retried uploads drains. Incident closed.

## What happened

The thumbnail generator in v4.7.0 was rewritten to invoke `ImageMagick` as an external process instead of using the previous in-process library. The dependency was added to the CI Dockerfile, which is where the change was tested, but the production container image is built from a separate Dockerfile that was not updated. The two files have drifted for some time; nothing in the build or deploy pipeline compares them or fails when a dependency exists in one and not the other.

The change should still have been caught by the integration suite, which does exercise the upload path end to end. It did not, because that suite mocks the thumbnail generator. The mock made the tests fast and deterministic and also made them blind to the one class of failure that mattered here, since the generator's actual runtime requirements are exactly what the mock stands in for. The suite passed against an artifact that could not perform the operation it was testing.

When the failure reached production it was invisible to monitoring for a reason that predates this release. The upload endpoint catches thumbnailing errors and returns HTTP 200 with a failure indicator in the response body, and our availability alert is defined on 5xx rate. From the alert's perspective the service was healthy and serving traffic normally for the entire outage. The first signal we received was human: support tickets accumulating over half an hour, then a further 22 minutes before anyone connected the ticket volume to a production problem. That 89-minute detection gap is the largest single component of the incident, considerably larger than the 41 minutes it took to diagnose and fix the problem once it had someone's attention.

## Remediation

The most urgent fix is the alerting gap, because it applies to failures we have not had yet. Upload success should be measured at the application level, on the outcome the service actually reports, not on HTTP status. Separately, the endpoint's habit of returning 200 for a server-side failure is a defect in its own right and should be corrected to return a 5xx, which would have made the existing alert fire. Both are worth doing: the status code should be honest, and the alert should not depend on it being honest. Every other alert defined on status code should be audited for the same assumption.

The build-side fixes address how the defect shipped. The production image and the CI image should be built from the same Dockerfile, with environment differences expressed as build arguments rather than as a parallel file; if that consolidation is too large to do immediately, an interim check that fails the build when the two files' installed packages diverge would have caught this specific change. The integration suite needs at least one path that runs the real thumbnail generator inside the production image, so that a missing runtime dependency surfaces before deploy rather than after.

Finally, support ticket volume was our only working detector and it took 51 minutes to reach an engineer. A threshold on ticket rate for a given product area, routed to the on-call engineer directly, would have compressed most of the detection gap even without any of the monitoring changes above.

Owners and target dates for each of these are not yet assigned and should be settled at the review.