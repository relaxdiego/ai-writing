# Incident Postmortem: Image Upload Failure (media-service v4.7.0)

**Date:** 2025-07-14
**Duration:** 09:12 – 11:48 UTC (2h 36m)
**Status:** Resolved
**Severity:** High — full loss of a core user-facing feature

---

## Summary

A deploy of `media-service` v4.7.0 introduced a dependency on the `ImageMagick` binary, which was not present in the production container image. Thumbnail generation failed on every upload, causing 100% of image uploads to fail for all users for approximately 2.5 hours. The failure was invisible to monitoring because the service returned HTTP 200 with an error body, so no alert fired. Detection came from customer support ticket volume roughly 49 minutes after the failure began. No data was lost.

## Impact

- **Users affected:** All users attempting image uploads
- **Failed uploads:** ~18,000
- **Data loss:** None. Uploads failed before persistence; clients retried successfully after recovery.
- **Duration of user-visible impact:** 09:14 – 10:44 UTC (1h 30m). Retried-upload backlog drained by 11:48 UTC.

## Timeline (UTC)

| Time | Event |
|---|---|
| 09:12 | `media-service` v4.7.0 deployed to production |
| 09:14 | Upload error rate rises from 0.2% to 100%. No alert fires — the alert measures 5xx rate, and the service returns HTTP 200 with an error body |
| 09:41 | First customer support ticket filed |
| 10:03 | Engineer notices elevated ticket volume and begins investigating |
| 10:20 | Root cause identified: v4.7.0 changed the thumbnail generator to require an `ImageMagick` binary absent from the production container image |
| 10:31 | Rollback to previous version started |
| 10:44 | Rollback complete; uploads recover |
| 11:48 | Backlog of retried uploads drains; incident closed |

**Time to detect:** 49 minutes (09:14 → 10:03)
**Time to diagnose:** 17 minutes (10:03 → 10:20)
**Time to mitigate:** 24 minutes (10:20 → 10:44)

## Root Cause

v4.7.0 changed the thumbnail generator to shell out to an `ImageMagick` binary. The production container image does not include that binary, so every thumbnail generation attempt failed, and every upload failed with it.

The defect reached production because three independent safeguards each had a gap:

1. **Build divergence.** The production container image is built from a different Dockerfile than the one used in CI. A dependency present in the CI image was therefore absent in production, and no stage of the pipeline compared the two.
2. **Test coverage gap.** The integration test suite mocks the thumbnail generator, so no test exercised the real binary path. The suite passed on a build that could not perform its primary function.
3. **Monitoring gap.** The upload alert measured HTTP status code rather than application-level success. Because the service returns 200 with an error body on failure, a 100% failure rate was indistinguishable from healthy traffic to the alerting system.

The third gap converted what could have been a several-minute incident into a 2.5-hour one. The failure was total and immediate at 09:14; detection depended entirely on humans noticing support tickets.

## What Went Well

- Once investigation began, diagnosis was fast (17 minutes) and the rollback path was clean and well understood.
- Client-side retry behavior meant no upload was permanently lost.

## What Went Poorly

- Nothing in the automated pipeline — not tests, not build validation, not alerting — detected a 100% failure of a core feature. Every layer was blind to this class of defect.
- Detection was accidental, depending on an engineer happening to notice ticket volume 49 minutes in.
- The 200-with-error-body response pattern actively concealed the failure from monitoring.

## Action Items

| # | Action | Type | Owner | Priority |
|---|---|---|---|---|
| 1 | Alert on application-level upload success rate, not HTTP status. Page when success rate drops below threshold over a short window. | Detect | *TBD* | P0 |
| 2 | Build the production container image from the same Dockerfile used in CI; eliminate the second Dockerfile. | Prevent | *TBD* | P0 |
| 3 | Add a smoke test that performs a real image upload end-to-end against the built production image, gating deploy. | Prevent | *TBD* | P0 |
| 4 | Add an integration test that exercises the real thumbnail generator without mocks. | Prevent | *TBD* | P1 |
| 5 | Return appropriate 5xx status codes for server-side upload failures instead of 200 with an error body. | Detect | *TBD* | P1 |
| 6 | Audit other alerts for the same status-code-vs-application-success mismatch. | Detect | *TBD* | P1 |
| 7 | Add automated post-deploy monitoring of key business metrics with auto-rollback on sharp regression. | Mitigate | *TBD* | P2 |

## Lessons

**A green test suite that mocks the thing that broke proves nothing about the thing that broke.** The integration tests mocked the exact component whose real-world dependency was missing.

**Monitor what users experience, not what the protocol reports.** An alert on HTTP status is a proxy for user success. When the proxy and the reality diverge — as they do whenever an application returns 200 on failure — the alert measures nothing.

**Two Dockerfiles for one artifact means CI validates a build that never ships.** Any divergence between the CI image and the production image is untested surface area by construction.

---

*Owners are marked TBD — please assign before this document is finalized.*