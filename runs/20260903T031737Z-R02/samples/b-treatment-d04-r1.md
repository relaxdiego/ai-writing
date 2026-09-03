# Incident Postmortem: Total Image Upload Failure

**Date:** 2025-07-14
**Duration:** 09:12–11:48 UTC (2h 36m)
**Severity:** Critical — full loss of a core user-facing feature
**Status:** Resolved

## Summary

A deploy of `media-service` v4.7.0 introduced a dependency on an `ImageMagick` binary that was not present in the production container image, causing every image upload to fail from 09:12 UTC onward. The failure was invisible to monitoring because the service returned HTTP 200 with an error body, so no alert fired and the outage was discovered only when support ticket volume drew an engineer's attention 51 minutes later. Roughly 18,000 uploads failed across all users during the window, though no data was lost — uploads were rejected at the thumbnail generation step rather than partially written, and retried uploads succeeded once the service was restored.

## Timeline (UTC)

| Time | Event |
|---|---|
| 09:12 | `media-service` v4.7.0 deployed to production |
| 09:14 | Upload error rate rises from 0.2% to 100%. No alert fires — the alert measures 5xx rate, and the service returns 200 with an error body |
| 09:41 | First customer support ticket filed |
| 10:03 | Engineer notices ticket volume and begins investigating |
| 10:20 | Root cause identified: v4.7.0 changed the thumbnail generator to require an `ImageMagick` binary absent from the production container image |
| 10:31 | Rollback to the previous version begins |
| 10:44 | Rollback complete; uploads recover |
| 11:48 | Backlog of retried uploads drains; incident closed |

## Root Cause

Version 4.7.0 rewrote the thumbnail generator to shell out to an `ImageMagick` binary. That binary exists in the image CI builds from but not in the one that ships to production, because the two are built from different Dockerfiles. Every upload therefore reached the thumbnail step, failed to find the binary, and returned an error — a failure mode that CI could never have caught, since the integration test suite mocks the thumbnail generator entirely and so exercised neither the real binary nor its absence.

## Contributing Factors

Three independent gaps lined up to let this reach production and stay there. The divergence between the CI Dockerfile and the production Dockerfile means the artifact CI validates is not the artifact users run, so any dependency added to one image without the other produces exactly this class of failure. The integration suite's mock of the thumbnail generator removed the last chance to catch it before deploy, trading fidelity for speed at precisely the boundary where the bug lived. Detection then failed on its own terms: the alert measured HTTP status rather than application-level success, and because the service reported failures as 200 responses with an error body, a 100% failure rate looked identical to perfect health. The 51 minutes between the failure and the first human noticing were spent entirely on a dashboard showing green.

## Resolution

Rolling back to the prior version restored the working container image and uploads recovered within 13 minutes of the rollback starting. Clients had been retrying failed uploads throughout the outage, and that accumulated backlog took a further hour to drain before the system returned to normal throughput and the incident was closed.

## Action Items

| Action | Rationale |
|---|---|
| Build production images from the same Dockerfile CI validates, or promote the CI-built artifact directly | Eliminates the class of bug where a dependency exists in one image and not the other |
| Add an alert on application-level upload success rate, independent of HTTP status | Detection would have fired at 09:14 rather than depending on support tickets at 09:41 |
| Add at least one integration test that exercises the real thumbnail generator against the production image | Closes the gap the mock left open |
| Audit remaining alerts for status-code proxies standing in for real success signals | The same blind spot likely exists elsewhere |
| Review whether 200-with-error-body is appropriate for upload failures | Correct status codes would have made the existing alert sufficient |

## What Went Well

Once an engineer engaged, diagnosis took 17 minutes and rollback was underway 11 minutes after that — the response was fast in absolute terms. The failure was also clean: uploads were rejected rather than partially written, so recovery required no data repair and client retry logic drained the backlog without manual intervention.