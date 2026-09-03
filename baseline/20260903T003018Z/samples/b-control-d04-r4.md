# Incident Postmortem: Image Upload Failure (media-service v4.7.0)

**Date:** 2025-07-14
**Duration:** 09:12 – 11:48 UTC (2h 36m)
**Status:** Resolved
**Severity:** High — total loss of a core user-facing function

---

## Summary

A deploy of `media-service` v4.7.0 introduced a dependency on an `ImageMagick` binary that was not present in the production container image. Every image upload failed from 09:12 UTC onward. Because the service returned HTTP 200 with an error body, the 5xx-rate alert never fired, and the failure went undetected by monitoring for 51 minutes until customer support tickets accumulated. Approximately 18,000 uploads failed. No data was lost.

## Impact

- **Users affected:** all users attempting image uploads
- **Failed uploads:** ~18,000
- **Data loss:** none — failed uploads were retryable and the backlog drained successfully
- **Detection path:** customer support tickets, not automated alerting

## Timeline (UTC)

| Time | Event |
|---|---|
| 09:12 | `media-service` v4.7.0 deployed to production |
| 09:14 | Upload error rate rises from 0.2% to 100%. No alert fires — the alert measures 5xx rate, and the service returns HTTP 200 with an error body |
| 09:41 | First customer support ticket received |
| 10:03 | Engineer notices ticket volume and begins investigating |
| 10:20 | Root cause identified: v4.7.0's thumbnail generator requires an `ImageMagick` binary absent from the production container image |
| 10:31 | Rollback started |
| 10:44 | Rollback complete; uploads recover |
| 11:48 | Backlog of retried uploads drains; incident closed |

**Key intervals:**
- Time to detect (automated): never — detection was human, via support tickets
- Time to human detection: 29 min (09:12 → 09:41 first ticket)
- Time to engineer engagement: 51 min (09:12 → 10:03)
- Time to diagnosis: 17 min (10:03 → 10:20)
- Time to mitigation: 24 min (10:20 → 10:44)
- Time to full recovery: 2h 36m

## Root Cause

v4.7.0 changed the thumbnail generator to shell out to an `ImageMagick` binary. That binary is present in the CI build environment but not in the production container image, so every thumbnail generation attempt — and therefore every upload — failed at runtime.

## Contributing Factors

1. **Divergent Dockerfiles.** The production container image is built from a different Dockerfile than the one used in CI. A dependency added and verified in CI carries no guarantee it exists in production. This made the failure invisible to every pre-production gate.

2. **Integration tests mock the thumbnail generator.** The one test layer that could have caught a missing runtime binary substitutes a mock for the component under test, so the suite passed against a build that could not generate a single thumbnail.

3. **Alerting measured transport status, not application success.** The upload alert was defined on 5xx rate. Because the service returns HTTP 200 with an error payload, a 100% application-level failure rate registered as a 0% alert-level failure rate. Monitoring was structurally incapable of seeing this class of outage.

Together these form a single pattern: three independent safety layers (CI, integration tests, alerting) each validated a proxy rather than the real thing — the CI image rather than the production image, a mock rather than the generator, HTTP status rather than upload success.

## What Went Well

- Once an engineer engaged, diagnosis took 17 minutes and mitigation 24 minutes.
- Rollback was clean and immediate; recovery followed within minutes.
- Retry behavior preserved user data — the backlog drained with no permanent loss.

## What Went Poorly

- The outage was detected by customers, not by us.
- 51 minutes elapsed between total failure and any engineer looking at the problem.
- Support ticket volume is not wired into any alerting path, so the 09:41–10:03 window depended on someone happening to notice.

## Action Items

| # | Action | Type | Priority |
|---|---|---|---|
| 1 | Alert on application-level upload success rate, not HTTP status. Page when success rate drops below threshold over a short window. | Detect | P0 |
| 2 | Build production images from the same Dockerfile used in CI; eliminate the second Dockerfile entirely. | Prevent | P0 |
| 3 | Add a post-deploy smoke test that performs a real end-to-end image upload against the deployed production image and fails the deploy if it does not succeed. | Prevent | P0 |
| 4 | Replace the thumbnail generator mock in the integration suite with a test that runs against the real binary in the real image. | Prevent | P1 |
| 5 | Audit remaining alerts for the same status-vs-outcome mismatch; any endpoint that can return 200 with an error body needs an application-level SLI. | Detect | P1 |
| 6 | Route support ticket volume spikes into the on-call alerting path as a backstop signal. | Detect | P2 |
| 7 | Review whether returning HTTP 200 on upload failure is correct API behavior; align status codes with outcomes. | Prevent | P2 |

## Lessons

The alert gap is the finding that generalizes furthest. An SLI defined on transport status silently stops measuring the thing it was meant to measure the moment an application handles its own errors. Any alert whose signal can be satisfied while the user-visible operation fails is not an alert. The Dockerfile divergence is the finding with the widest blast radius — it invalidates *every* CI guarantee for *every* service built this way, not just this one dependency, and should be treated as a standing risk until closed.