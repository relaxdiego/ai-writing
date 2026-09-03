# Incident Postmortem: Image Upload Failure (media-service v4.7.0)

**Date:** 2025-07-14
**Duration:** 09:12–11:48 UTC (2h 36m)
**Severity:** Critical — total loss of a core feature
**Status:** Resolved

---

## Summary

A deploy of `media-service` v4.7.0 introduced a dependency on an `ImageMagick` binary that was not present in the production container image. Thumbnail generation failed for every upload, causing 100% of image uploads to fail for all users. Because the service returned HTTP 200 with an error body, no alert fired. The failure was detected 49 minutes later through customer support ticket volume, and resolved by rollback.

**Impact:** ~18,000 failed uploads across all users. No data loss; failed uploads were retried successfully after recovery.

---

## Timeline (UTC)

| Time | Event |
|---|---|
| 09:12 | `media-service` v4.7.0 deployed to production |
| 09:14 | Upload error rate rises from 0.2% to 100%. No alert fires — alerting was keyed on 5xx rate, and the service returned HTTP 200 with an error body |
| 09:41 | First customer support ticket filed |
| 10:03 | Engineer notices elevated ticket volume and begins investigating |
| 10:20 | Root cause identified: v4.7.0 changed the thumbnail generator to shell out to an `ImageMagick` binary absent from the production container image |
| 10:31 | Rollback started |
| 10:44 | Rollback complete; uploads recover |
| 11:48 | Backlog of retried uploads drains; incident closed |

**Time to detect:** 49 min (09:14 → 10:03)
**Time to mitigate:** 41 min from detection (10:03 → 10:44)
**Total customer impact:** 1h 32m of failed uploads, plus 1h 4m of backlog drain

---

## Root Cause

Version 4.7.0 modified the thumbnail generator to invoke an `ImageMagick` binary. The production container image does not include that binary, so every thumbnail generation attempt failed, and every upload failed with it.

The change passed CI and code review because three independent safeguards each had a gap that aligned:

1. **Divergent build definitions.** The production container image is built from a different Dockerfile than the one used in CI. A dependency added to the CI image is not automatically present in production, and nothing detects the drift.
2. **Over-mocked integration tests.** The integration test suite mocks the thumbnail generator, so no test exercised the real binary invocation path. The tests would have passed even with the binary missing from *both* images.
3. **Alerting on the wrong signal.** The upload alert measured HTTP status codes. The service signals upload failure with HTTP 200 and an error body, so a 100% failure rate was invisible to monitoring.

Any one of these gaps closed would likely have caught the incident before customers did.

---

## What Went Well

- Once investigation started, root cause was identified in 17 minutes.
- Rollback was fast (13 min) and clean.
- Upload retry behavior meant no user data was lost; the backlog drained without manual intervention.

## What Went Poorly

- Detection depended entirely on customers reporting the problem. We had a total outage of a core feature and our monitoring reported healthy.
- 49 minutes elapsed between total failure and any engineer looking at it; support ticket volume is not a paging signal.
- The gap between CI and production build definitions is a latent risk that applies to every dependency, not just this one.

---

## Action Items

| # | Action | Type | Owner | Priority |
|---|---|---|---|---|
| 1 | Alert on application-level upload success rate, not HTTP status. Page on a sustained drop below threshold. | Detect | *TBD* | P0 |
| 2 | Build the production container image from the same Dockerfile used in CI, or add a CI check that fails when the two diverge. | Prevent | *TBD* | P0 |
| 3 | Add at least one integration test that exercises the real thumbnail generator against the actual container image, with no mocking. | Prevent | *TBD* | P1 |
| 4 | Audit other services for the same 200-with-error-body pattern and confirm each has an application-level alert. | Detect | *TBD* | P1 |
| 5 | Add a post-deploy smoke test that performs a real upload against production and fails the deploy on error. | Detect | *TBD* | P1 |
| 6 | Route sustained support-ticket spikes on a single topic into an on-call signal. | Detect | *TBD* | P2 |

---

## Lessons

**Health checks must measure what users experience.** A 200 response is not evidence that the request succeeded. Any endpoint that can fail while returning 2xx needs an alert on the application-level outcome.

**Mocks at the integration layer hide integration failures.** The thumbnail generator mock removed the only test that could have caught a missing binary. Integration tests should exercise the boundary they are named for.

**Build environment drift is a silent dependency risk.** Two Dockerfiles for the same service guarantee that some dependency will eventually exist in one and not the other. The failure mode is arbitrary and only surfaces in production.