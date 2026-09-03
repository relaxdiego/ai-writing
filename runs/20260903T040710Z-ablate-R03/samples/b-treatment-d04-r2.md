# Postmortem: image upload failure following media-service v4.7.0

**Date:** 2025-07-14, 09:12–11:48 UTC (2h36m)
**Impact:** Image uploads failed for all users for the duration of the incident, producing roughly 18,000 failed uploads. No data was lost; failed uploads were rejected rather than partially written, and the retry backlog drained cleanly once the service recovered.

## Summary

Version 4.7.0 of `media-service` changed the thumbnail generator to shell out to an `ImageMagick` binary. That binary is present in the image CI builds but not in the image that runs in production, so every upload that reached the thumbnail step failed immediately after the deploy. The failure was invisible to monitoring because the service returned HTTP 200 with an error body, and the upload alert was defined on 5xx rate. We learned about the outage from customers, and detection took 51 minutes from the first support ticket and 111 minutes from the start of impact. Recovery was a straightforward rollback.

## Timeline (UTC)

- **09:12** — `media-service` v4.7.0 deployed to production.
- **09:14** — Upload error rate rises from 0.2% to 100%. No alert fires.
- **09:41** — First customer support ticket.
- **10:03** — An engineer notices the ticket volume and begins investigating.
- **10:20** — Cause identified: v4.7.0 requires an `ImageMagick` binary absent from the production container image.
- **10:31** — Rollback to the prior version begins.
- **10:44** — Rollback complete; uploads recover.
- **11:48** — Backlog of retried uploads drains. Incident closed.

## Root cause

The production container image is built from a different Dockerfile than the one used in CI. The CI image includes `ImageMagick`; the production image does not. Because the two artifacts diverge, a passing build carries no guarantee that the same code runs in production, and v4.7.0's new runtime dependency was satisfied in every environment where it was tested and in none where it mattered.

## Contributing factors

Three separate defences failed, and each would have caught this alone. The build pipeline tests one artifact and ships another, so the missing dependency was never exercised. The integration suite mocks the thumbnail generator, so no test invoked the real binary even in the environment that had it. And the upload alert measured HTTP status rather than application-level success, while the upload endpoint answers failures with 200 and an error body; the two decisions are individually defensible and jointly meant that a total outage looked, to our monitoring, like a healthy service.

## What went well

Once an engineer was looking at the problem, diagnosis took 17 minutes and rollback took 13. The retry path behaved correctly under a sustained total failure and drained without manual intervention or data loss.

## Action items

The single Dockerfile is the highest-value fix: CI should build the production image and the deploy should promote that exact artifact, so nothing that has not been tested can reach production. Alongside it, the upload alert needs to move to an application-level success-rate signal, and the upload endpoint should return a 5xx status for server-side failures so that generic infrastructure alerting sees them too. The integration suite needs at least one test that exercises the real thumbnail generator against the shipped image, since a mock cannot detect a missing binary. Lastly, 51 minutes passed between the first customer ticket and any engineering response, and a support-volume signal routed to the on-call engineer would have compressed most of that gap.

Owners and target dates for each of these remain to be assigned at the incident review.