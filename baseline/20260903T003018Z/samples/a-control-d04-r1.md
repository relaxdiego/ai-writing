# Incident Postmortem: Image Upload Failures (media-service v4.7.0)

**Date:** 2025-07-14
**Duration:** 09:12–11:48 UTC (2h 36m); user-facing failures 09:14–10:44 UTC (1h 30m)
**Severity:** Full outage of a core feature
**Status:** Resolved

## Summary

A deploy of `media-service` v4.7.0 introduced a dependency on an `ImageMagick` binary that was not present in the production container image. Thumbnail generation failed for every upload, and because the service returned HTTP 200 with an error body, no alert fired. The failure was discovered 49 minutes later through customer support ticket volume and resolved by rolling back to the prior version.

## Impact

- Image uploads failed for **all users** for approximately 1h 30m.
- Approximately **18,000 uploads failed**.
- **No data loss.** Failed uploads were retried successfully; the retry backlog drained by 11:48 UTC.

## Timeline (UTC)

| Time | Event |
|---|---|
| 09:12 | `media-service` v4.7.0 deployed to production |
| 09:14 | Upload error rate rises from 0.2% to 100%. No alert fires — the alert measures 5xx rate, and the service returns 200 with an error body |
| 09:41 | First customer support ticket filed |
| 10:03 | Engineer notices elevated ticket volume and begins investigating |
| 10:20 | Root cause identified: v4.7.0 requires an `ImageMagick` binary absent from the production container image |
| 10:31 | Rollback started |
| 10:44 | Rollback complete; uploads recover |
| 11:48 | Retry backlog drains; incident closed |

## Root cause

v4.7.0 changed the thumbnail generator to shell out to an `ImageMagick` binary. That binary is not installed in the production container image, so every thumbnail generation attempt failed, and with it every upload.

The defect reached production because production containers are built from a **different Dockerfile** than the one used in CI. The CI image happened to satisfy the new dependency; the production image did not. Nothing in the pipeline compares the two.

The defect was not caught in testing because the **integration test suite mocks the thumbnail generator**. The tests exercised the calling code but never the binary invocation, so a missing runtime dependency was invisible to them.

The defect was not detected in production because the **upload alert measures HTTP status rather than application-level success**. The service returned 200 with an error body on failure, so a 100% failure rate looked identical to a 100% success rate from the alert's perspective.

## Detection and response

Detection was entirely manual and customer-driven: 27 minutes from failure to the first support ticket, and 49 minutes from failure to an engineer investigating. Once investigation began, response was fast — 17 minutes to root cause, 11 minutes to complete the rollback. Nearly all of the user-facing outage was time spent not knowing.

## What went well

- Diagnosis was quick once someone looked, aided by the obvious correlation with a fresh deploy.
- Rollback was clean and took 13 minutes end to end.
- Upload retries preserved user data; no work was lost.

## What went wrong

- The three independent safeguards that should have caught this — build parity, integration tests, and alerting — each had a gap, and the gaps lined up.
- Returning 200 on a failed operation defeated monitoring and likely confused client-side retry behavior as well.
- Support ticket volume was the detection mechanism, and there was no automatic signal from it; it depended on an engineer happening to notice.

## Action items

| # | Action | Addresses | Owner | Due |
|---|---|---|---|---|
| 1 | Alert on application-level upload success rate, not HTTP status | Detection gap | TBD | TBD |
| 2 | Build production images from the same Dockerfile used in CI; remove the second Dockerfile | Build parity | TBD | TBD |
| 3 | Add a smoke test that runs against the actual production image and generates a real thumbnail, gating deploys | Test gap, build parity | TBD | TBD |
| 4 | Make the thumbnail generator return a non-2xx status when it fails; audit other endpoints for 200-on-error | Detection gap | TBD | TBD |
| 5 | Add a startup check that verifies required external binaries are present and fails the container if not | Class of failure | TBD | TBD |
| 6 | Alert on support ticket volume spikes as a backstop detection signal | Detection gap | TBD | TBD |

Items 1 and 4 are the highest leverage: either alone would have cut roughly 45 minutes off this outage. Item 5 would have turned a silent 100% failure into a failed deploy.

## Open questions

- Did client-side retry logic treat the 200-with-error-body responses as successes? If so, some users may have seen silent failures rather than errors.
- How long have the CI and production Dockerfiles been divergent, and what else differs between them?

---

Owners and dates are left as TBD — tell me who's on the hook and I'll fill them in. Happy to also drop this into a file in the repo if you want it tracked.