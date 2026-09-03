# Incident Postmortem: Image Upload Failure (media-service v4.7.0)

**Date:** 2025-07-14
**Duration:** 09:12–11:48 UTC (2h 36m); user-visible upload failures 09:14–10:44 UTC (1h 30m)
**Severity:** High — total loss of a core feature for all users
**Status:** Resolved
**Author:** Mark Maglana

## Summary

A deploy of `media-service` v4.7.0 introduced a dependency on the `ImageMagick` binary, which is not present in the production container image. Thumbnail generation failed for every upload. Because the failure path returned HTTP 200 with an error body, the 5xx-based alert never fired, and the outage was detected only after customer support ticket volume rose — 49 minutes after impact began. Rolling back to v4.6.x restored service.

## Impact

- Image uploads failed for **all users** from 09:14 to 10:44 UTC.
- Approximately **18,000 uploads failed**.
- **No data loss.** Failed uploads were retried successfully; the retry backlog drained by 11:48 UTC.
- Users saw upload errors for the full 90-minute window and degraded upload latency during the backlog drain.

## Timeline (UTC)

| Time | Event |
|---|---|
| 09:12 | `media-service` v4.7.0 deployed to production |
| 09:14 | Upload error rate rises from 0.2% to 100%. No alert fires — the alert is keyed on 5xx rate, and the service returns 200 with an error body |
| 09:41 | First customer support ticket filed (**27 min** of undetected impact) |
| 10:03 | Engineer notices elevated ticket volume and begins investigating (**49 min** to detection) |
| 10:20 | Root cause identified: v4.7.0's thumbnail generator requires the `ImageMagick` binary, absent from the production container image |
| 10:31 | Rollback started |
| 10:44 | Rollback complete; uploads recover (**90 min** total user-visible impact) |
| 11:48 | Retried-upload backlog drains; incident closed |

**Key intervals:** time to detect 49m · time to diagnose 17m · time to mitigate 24m · time to full recovery 64m after mitigation.

## Root Cause

v4.7.0 changed the thumbnail generator to shell out to the `ImageMagick` binary. That binary is installed in the Dockerfile used by CI but not in the Dockerfile used to build the production image. Every thumbnail generation attempt therefore failed at runtime in production, and the upload endpoint returned an application-level error inside a 200 response.

## Contributing Factors

**1. Divergent Dockerfiles.** The production container image is built from a different Dockerfile than the one CI uses. This means the artifact validated by CI is not the artifact that runs in production, and any runtime dependency added to one file can silently be missing from the other. This is the direct cause of the defect reaching production.

**2. Integration tests mock the thumbnail generator.** The integration suite substitutes a mock for the thumbnail generator, so no test in the pipeline ever executed the real code path that invokes `ImageMagick`. A missing binary was structurally undetectable by the test suite regardless of coverage.

**3. The alert measured transport status, not application success.** The upload alert was defined on HTTP 5xx rate. The failure path returned 200 with an error body, so a 100% functional failure rate registered as a 0% alert signal. Detection fell back to customer support tickets, which added 49 minutes to the outage.

Each of these is independently sufficient to explain a piece of the incident: the first let the bug ship, the second let it pass review, the third let it run undetected.

## What Went Well

- Once investigation began, diagnosis took 17 minutes and mitigation was underway 11 minutes after that.
- Rollback was clean and effective, with no manual intervention required.
- Upload retry behavior worked as designed — the backlog drained without operator action and no user data was lost.

## Action Items

Owners and target dates are placeholders pending assignment.

| # | Action | Type | Priority |
|---|---|---|---|
| 1 | Build the production image from the same Dockerfile CI validates, or promote the CI-built artifact directly to production | Prevention | P0 |
| 2 | Add a smoke test that exercises the real thumbnail generation path (unmocked) against the built production image before promotion | Detection | P0 |
| 3 | Replace the 5xx-based upload alert with one on application-level upload success rate; page on sustained deviation from baseline | Detection | P0 |
| 4 | Audit remaining alerts for other cases where HTTP status is used as a proxy for application success | Detection | P1 |
| 5 | Change the upload endpoint to return an appropriate non-2xx status when the operation fails | Correctness | P1 |
| 6 | Add a post-deploy canary check on core upload success rate with automatic rollback on regression | Mitigation | P1 |
| 7 | Route support ticket volume spikes on core features into an on-call signal | Detection | P2 |

## Open Questions

- Why do CI and production use separate Dockerfiles? Understanding the original reason matters before consolidating them.
- Were any other runtime dependencies added recently that exist in the CI image but not in production? A one-time diff of the two images would surface this.
- Did the ~18,000 failed uploads all retry successfully, or did some users abandon the flow? Worth confirming against upload funnel metrics before stating "no user impact beyond the window."