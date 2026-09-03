# Incident Postmortem: Image Upload Failure (media-service v4.7.0)

**Date:** 2025-07-14
**Duration:** 09:12–11:48 UTC (2h 36m)
**Severity:** Full outage of image upload functionality
**Status:** Resolved

## Summary

A deploy of `media-service` v4.7.0 introduced a dependency on the `ImageMagick` binary, which was not present in the production container image. All image uploads failed for 2 hours and 36 minutes. Because the service returned HTTP 200 with an error body, no alert fired, and the failure was discovered only after customer support ticket volume rose — 51 minutes after the first ticket, and 89 minutes after the failures began.

## Impact

- Image uploads failed for **all users** for the duration of the incident.
- Approximately **18,000 uploads failed**.
- **No data loss.** Failed uploads were retried and drained successfully after recovery.
- Customer support absorbed an unmeasured volume of tickets beginning at 09:41.

## Timeline (UTC)

| Time | Event |
|---|---|
| 09:12 | `media-service` v4.7.0 deployed to production |
| 09:14 | Upload error rate rises from 0.2% to 100%. No alert fires — the alert measured 5xx rate, and the service returned HTTP 200 with an error body |
| 09:41 | First customer support ticket filed (27 min undetected) |
| 10:03 | Engineer notices ticket volume and begins investigating (49 min from first ticket) |
| 10:20 | Root cause identified: v4.7.0's thumbnail generator requires the `ImageMagick` binary, which is absent from the production container image |
| 10:31 | Rollback started |
| 10:44 | Rollback complete; uploads recover (**time to recovery: 1h 32m**) |
| 11:48 | Backlog of retried uploads drains; incident closed |

**Key intervals:** Time to detect 49m (09:14 → 10:03). Time to diagnose 17m (10:03 → 10:20). Time to mitigate 24m (10:20 → 10:44).

## Root Cause

v4.7.0 changed the thumbnail generator to shell out to the `ImageMagick` binary. The production container image does not include that binary, so every thumbnail generation attempt failed, and with it every upload.

The defect reached production because **the production container image is built from a different Dockerfile than the one used in CI**. CI validated an image that was not the artifact being deployed, so the missing binary was structurally undetectable before deploy.

## Contributing Factors

1. **Divergent Dockerfiles.** CI builds and tests one image; production deploys another. Any dependency present in the CI image but absent from the production image will pass all tests and fail on deploy. This is the primary reason the bug shipped.

2. **Integration tests mock the thumbnail generator.** The one test layer that could have exercised the real binary substituted a mock instead, so the new dependency was never actually invoked in any automated test.

3. **The alert measured HTTP status, not application-level success.** The service returned `200 OK` with an error body on failure. The alert watched 5xx rate, so a 100% failure rate registered as a 100% success rate. This turned a ~2-minute detection into a ~49-minute one and made customer support the de facto monitoring system.

Factors 1 and 2 allowed the defect to ship. Factor 3 determined how long it lasted.

## What Went Well

- Once investigation began, diagnosis was fast (17 minutes to root cause).
- Rollback was available, executed promptly, and worked cleanly.
- The retry mechanism preserved all failed uploads — no data loss despite a full outage.

## What Went Poorly

- Detection depended entirely on humans reading support tickets.
- 27 minutes passed between the first customer ticket and any support signal reaching engineering; another 22 before someone acted on it.
- Automated testing gave false confidence: the test suite passed on an artifact that was not the one deployed.

## Action Items

| # | Action | Type | Priority |
|---|---|---|---|
| 1 | Build the production container image from the same Dockerfile CI tests against; make the CI-tested image the deployed artifact | Prevention | **High** |
| 2 | Alert on application-level upload success rate, not HTTP status code; audit other alerts for the same status-vs-semantics gap | Detection | **High** |
| 3 | Add a smoke test that exercises the real thumbnail generator against the production image (no mocking) before the deploy promotes | Prevention | **High** |
| 4 | Return a 5xx status when uploads fail, rather than 200 with an error body | Prevention | Medium |
| 5 | Add a post-deploy canary check on upload success rate with automatic rollback on regression | Detection | Medium |
| 6 | Route support ticket volume spikes to an on-call signal so ticket surges page rather than wait to be noticed | Detection | Medium |

## Lessons

An alert that measures the wrong signal is worse than no alert, because it implies coverage that does not exist. The 5xx alert was working correctly and reported healthy throughout a total outage.

Likewise, a test suite that validates a different artifact than the one deployed provides confidence without safety. The gap between the CI Dockerfile and the production Dockerfile is the kind of drift that produces exactly this failure — one that is invisible until deploy and obvious immediately afterward.