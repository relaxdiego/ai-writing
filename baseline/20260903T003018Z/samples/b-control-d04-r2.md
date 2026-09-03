# Incident Postmortem: Total Image Upload Failure (media-service v4.7.0)

**Date:** 2025-07-14
**Duration:** 09:12–11:48 UTC (2h 36m)
**Severity:** SEV-1 (full loss of a core user-facing feature)
**Status:** Resolved
**Author:** kind.water4546@fastmail.com

---

## Summary

A routine deploy of `media-service` v4.7.0 introduced a dependency on an `ImageMagick` binary that was not present in the production container image. Every image upload failed immediately after the deploy. Because the service returned HTTP 200 with an error body, the 5xx-rate alert never fired, and the failure went undetected by monitoring for 49 minutes — surfacing only through customer support tickets. The incident was resolved by rolling back to the previous version.

## Impact

- **Image uploads failed for 100% of users** for 92 minutes (09:12–10:44 UTC).
- **~18,000 uploads failed.**
- **No data loss.** Retried uploads succeeded; the retry backlog fully drained by 11:48 UTC.
- Upload error rate went from a 0.2% baseline to 100%.

## Timeline (UTC)

| Time | Event |
|---|---|
| 09:12 | `media-service` v4.7.0 deployed to production |
| 09:14 | Upload error rate rises from 0.2% to 100%. **No alert fires** — the alert measured 5xx rate, and the service returned 200 with an error body |
| 09:41 | First customer support ticket filed (27 min of silent failure) |
| 10:03 | Engineer notices elevated ticket volume and begins investigating |
| 10:20 | Root cause identified: v4.7.0's thumbnail generator requires an `ImageMagick` binary absent from the production container image |
| 10:31 | Rollback started |
| 10:44 | Rollback complete; uploads recover (**user impact ends**) |
| 11:48 | Retried-upload backlog drains; incident closed |

**Key intervals:** 49 min to detection (customer-reported) · 17 min to diagnosis · 24 min to recovery.

## Root Cause

v4.7.0 changed the thumbnail generator to shell out to an `ImageMagick` binary. That binary was not installed in the production container image, so every thumbnail generation attempt — and therefore every upload — failed.

The defect reached production because the production container image is built from a **different Dockerfile** than the one used in CI. The CI image happened to contain `ImageMagick`; the production image did not. No stage of the pipeline exercised the production image against real thumbnail generation.

## Contributing Factors

1. **Divergent build definitions.** Production and CI build from separate Dockerfiles. CI therefore validates an artifact that is not the one shipped, so any environment difference is invisible until production.
2. **Integration tests mock the thumbnail generator.** The test suite could not have caught a missing binary — the code path that invokes `ImageMagick` is never executed against a real dependency in any automated test.
3. **Alerting measured transport status, not application success.** The alert watched HTTP 5xx rate. Because the service returned `200` with an error payload, a 100% failure rate registered as a 100% success rate. This turned a would-be 2-minute detection into a 49-minute, customer-reported one.

## What Went Well

- Once investigation began, diagnosis was fast (17 minutes) and the rollback path was clean and effective.
- Client-side retry behavior preserved user data — no uploads were permanently lost.

## Action Items

| # | Action | Type | Owner | Priority |
|---|---|---|---|---|
| 1 | Alert on application-level upload success rate, not HTTP status. Page when success rate drops below threshold over a short window. | Detect | TBD | P0 |
| 2 | Build production and CI images from a single Dockerfile; make CI test the exact artifact that ships (promote the built image, don't rebuild). | Prevent | TBD | P0 |
| 3 | Add a smoke test that runs against the real production image and performs one end-to-end upload with real thumbnail generation — no mocks — as a deploy gate. | Prevent | TBD | P0 |
| 4 | Audit remaining alerts for the same status-vs-outcome gap; any endpoint that can return 200 on failure needs an application-level signal. | Detect | TBD | P1 |
| 5 | Add post-deploy canary/automatic-rollback on error-rate regression so a bad deploy self-reverts rather than waiting for human detection. | Mitigate | TBD | P1 |
| 6 | Fix the service to return an appropriate 5xx on thumbnail generation failure. | Prevent | TBD | P2 |

## Lessons Learned

The core lesson is that **we monitored a proxy for health rather than health itself**. A service can be perfectly available at the HTTP layer while delivering zero value to users. Any alert defined on transport-layer signals should be treated as incomplete until paired with an application-level outcome metric.

Secondarily, **CI is only as trustworthy as the artifact it tests**. Testing a build that differs from the shipped build converts CI from a safety net into a source of false confidence — an entire class of dependency and environment bugs passes straight through.