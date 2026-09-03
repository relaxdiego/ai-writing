# Incident Postmortem: Image Upload Failure (2025-07-14)

**Duration:** 2025-07-14 09:12–11:48 UTC (2h 36m)
**Impact:** Image uploads failed for all users. Approximately 18,000 uploads failed. No data loss.

## Summary

A deploy of `media-service` v4.7.0 introduced a dependency on the `ImageMagick` binary, which is absent from the production container image. Every upload failed immediately after the deploy. Because the service returned HTTP 200 with an error body, the 5xx-rate alert never fired, and the failure went undetected for 51 minutes until customer support tickets accumulated.

## Timeline (UTC)

| Time | Event |
|---|---|
| 09:12 | `media-service` v4.7.0 deployed |
| 09:14 | Upload error rate rises from 0.2% to 100%. No alert fires — the alert measures 5xx rate, and the service returns 200 with an error body |
| 09:41 | First customer support ticket |
| 10:03 | Engineer notices ticket volume and begins investigating |
| 10:20 | Root cause identified: v4.7.0 requires an `ImageMagick` binary not present in the production container image |
| 10:31 | Rollback started |
| 10:44 | Rollback complete; uploads recover |
| 11:48 | Backlog of retried uploads drains; incident closed |

Time to detection: 51 minutes. Time to mitigation: 1h 32m.

## Root Cause

v4.7.0 changed the thumbnail generator to shell out to an `ImageMagick` binary. The production container image does not include that binary, so thumbnail generation — and therefore every upload — failed at runtime.

## Contributing Factors

**The production container image is built from a different Dockerfile than the one used in CI.** CI validated an image that was not the image shipped to production, so the missing dependency was never exercised before deploy.

**The integration test suite mocks the thumbnail generator.** No test invoked the real binary, so no test could have caught its absence regardless of which image was used.

**The alert measured HTTP status rather than application-level success.** The service signalled failure in the response body while returning 200, so a 100% failure rate was invisible to monitoring. Detection fell back on customer reports.

## Action Items

- Build production and CI container images from a single Dockerfile, or gate deploys on the image CI actually tested.
- Add at least one integration test that exercises the real thumbnail generator against the production image.
- Replace the 5xx-rate alert on the upload path with an alert on application-level upload success rate.
- Audit other services for the same 200-with-error-body pattern and the alerting blind spot it creates.