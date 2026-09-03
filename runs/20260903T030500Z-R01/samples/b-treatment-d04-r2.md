# Incident Postmortem: Image Upload Failure (2025-07-14)

**Duration:** 2025-07-14 09:12–11:48 UTC (2h 36m)
**Impact:** Image uploads failed for all users. Approximately 18,000 uploads failed. No data loss.

## Summary

Version 4.7.0 of `media-service` changed the thumbnail generator to shell out to an `ImageMagick` binary that was not present in the production container image. Every upload failed immediately after the deploy. The failure returned HTTP 200 with an error body, so the 5xx-rate alert never fired, and the outage was found through customer support tickets 49 minutes later.

## Timeline (UTC)

| Time | Event |
|---|---|
| 09:12 | `media-service` v4.7.0 deployed |
| 09:14 | Upload error rate rises from 0.2% to 100%. No alert fires — the alert measures 5xx rate, and the service returns 200 with an error body |
| 09:41 | First customer support ticket |
| 10:03 | Engineer notices ticket volume, begins investigating |
| 10:20 | Root cause identified: v4.7.0 requires an `ImageMagick` binary absent from the production container image |
| 10:31 | Rollback started |
| 10:44 | Rollback complete; uploads recover |
| 11:48 | Retry backlog drains; incident closed |

## Root cause

The v4.7.0 thumbnail generator invoked an `ImageMagick` binary as an external dependency. The production container image does not include that binary, so thumbnail generation failed on every upload, and the upload request failed with it.

## Contributing factors

**The production container image is built from a different Dockerfile than the one used in CI.** CI validated an image that was not the image that shipped, so a missing system dependency could pass every test and still be absent in production.

**The integration test suite mocks the thumbnail generator.** No test exercised the real binary invocation, so the missing dependency had no path to surface before deploy.

**The alert measured HTTP status rather than application-level success.** The service signalled failure in the response body while returning 200, which the alert treated as healthy. Detection fell back to customer support tickets, costing roughly 49 minutes.

## What went well

Once investigation began, diagnosis took 17 minutes and rollback completed 24 minutes after that. No uploads were lost — the retry backlog drained cleanly.

## Action items

1. **Build production images from the Dockerfile that CI tests**, or test the exact image that ships. This is the fix that would have prevented the incident outright.
2. **Alert on application-level upload success rate**, not HTTP status. A 100% failure rate should page within minutes regardless of status code.
3. **Add at least one integration test that runs the real thumbnail generator** against the production image, rather than a mock.
4. **Audit other alerts for the same status-vs-outcome gap** — any endpoint that can return 200 on failure is currently unmonitored in the same way.
5. **Review whether the service should return 200 on upload failure at all.** The status code should reflect the outcome.