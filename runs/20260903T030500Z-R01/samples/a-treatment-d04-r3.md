# Incident Postmortem: Image Upload Failure

**Date:** 2025-07-14
**Duration:** 09:12–11:48 UTC (2h 36m)
**Impact:** Image uploads failed for all users. Roughly 18,000 uploads failed. No data loss.
**Status:** Resolved

## Summary

A deploy of `media-service` v4.7.0 introduced a dependency on an `ImageMagick` binary that was not present in the production container image. Every upload failed immediately after the deploy. The service returned HTTP 200 with an error body, so the 5xx-rate alert never fired, and the failure went unnoticed for 51 minutes until customer tickets accumulated. Detection depended entirely on humans noticing ticket volume.

## Timeline (UTC)

| Time | Event |
|---|---|
| 09:12 | `media-service` v4.7.0 deployed |
| 09:14 | Upload error rate rises from 0.2% to 100%. No alert fires — the alert measures 5xx rate, and the service returns 200 with an error body |
| 09:41 | First customer support ticket |
| 10:03 | Engineer notices ticket volume and begins investigating |
| 10:20 | Root cause identified: v4.7.0 requires an `ImageMagick` binary absent from the production container image |
| 10:31 | Rollback started |
| 10:44 | Rollback complete; uploads recover |
| 11:48 | Backlog of retried uploads drains; incident closed |

Time to detection: 51 minutes (09:14 → 10:03). Time to mitigation: 92 minutes (09:12 → 10:44).

## Root Cause

v4.7.0 changed the thumbnail generator to shell out to an `ImageMagick` binary. The production container image does not include that binary, so every thumbnail generation attempt failed, and with it every upload.

## Contributing Factors

**The production container image is built from a different Dockerfile than the one used in CI.** CI validated an image that was not the image we shipped. A missing runtime dependency in production is invisible to any test that runs against the CI image.

**The integration test suite mocks the thumbnail generator.** The one test layer positioned to catch a missing binary replaced the code path that would have exercised it. The tests passed because they never invoked the generator.

**The alert measured HTTP status rather than application-level success.** A 100% failure rate produced no signal because the failures were shaped as 200 responses. The alert was measuring the transport, not the outcome.

These compound: the build gap meant the defect reached production, the test mock meant nothing caught it earlier, and the alert gap meant nothing caught it afterward.

## What Went Well

Once the investigation started, diagnosis took 17 minutes and rollback was complete 24 minutes after that. No data was lost — failed uploads were retried and drained cleanly.

## Action Items

| Action | Rationale |
|---|---|
| Build the production image from the same Dockerfile CI tests against, or test the production image directly | Closes the gap that let a missing dependency ship |
| Alert on application-level upload success rate, not HTTP status | The current alert cannot detect failures returned as 200 |
| Return a non-2xx status when an upload fails | The response shape misrepresents the outcome to every downstream consumer, not just the alert |
| Run at least one integration test against the real thumbnail generator | A fully-mocked dependency cannot fail in test the way it failed in production |
| Add a smoke test that performs a real upload against a newly deployed image before traffic shifts | Would have caught this within seconds of 09:12 |

## Open Questions

- Why does the production Dockerfile differ from the CI one? Whether this was deliberate (image size, base image, build secrets) determines whether the fix is convergence or testing the production image directly.
- Were other services affected by the same 200-with-error-body pattern, or is this specific to `media-service`?