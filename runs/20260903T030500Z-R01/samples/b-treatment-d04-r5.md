# Incident Postmortem: Image Upload Failure (2025-07-14)

**Duration:** 2025-07-14 09:12–11:48 UTC (2h 36m)
**Impact:** Image uploads failed for all users. Roughly 18,000 uploads failed. No data loss.

## Summary

A deploy of `media-service` v4.7.0 introduced a dependency on an `ImageMagick` binary that was not present in the production container image. Thumbnail generation failed on every upload. Because the service returned HTTP 200 with an error body, the 5xx-based alert never fired, and the failure was discovered only after customer support tickets accumulated — 51 minutes after the first ticket, and 111 minutes after the failure began.

## Timeline (UTC)

| Time | Event |
|---|---|
| 09:12 | `media-service` v4.7.0 deployed |
| 09:14 | Upload error rate rises from 0.2% to 100%. No alert fires. |
| 09:41 | First customer support ticket |
| 10:03 | Engineer notices ticket volume, begins investigating |
| 10:20 | Root cause identified: v4.7.0 requires `ImageMagick`, absent from the production image |
| 10:31 | Rollback started |
| 10:44 | Rollback complete; uploads recover |
| 11:48 | Backlog of retried uploads drains; incident closed |

## Root cause

v4.7.0 changed the thumbnail generator to shell out to an `ImageMagick` binary. The production container image does not include that binary, so every thumbnail generation attempt failed, and with it every upload.

## Contributing factors

**The production image is built from a different Dockerfile than the one used in CI.** CI validated an image that was not the image that shipped, so a missing runtime dependency could pass every gate and still fail in production.

**The integration test suite mocks the thumbnail generator.** No test in the pipeline executed the real binary, so the new dependency was never exercised against a real image.

**The alert measured HTTP status rather than application-level success.** The service returned 200 with an error body on failure. A 100% application failure rate was invisible to monitoring, and detection fell to customer support.

These three compound: the first let a broken image ship, the second let it ship undetected, and the third let it stay broken for 111 minutes.

## What went well

Once the investigation began, diagnosis took 17 minutes and rollback was complete 24 minutes after that. Retried uploads drained without intervention and no data was lost.

## Action items

1. **Build the production image from the Dockerfile CI tests.** Whatever the reason for the split, the shipped artifact must be the tested artifact — ideally, CI builds the image once and the same digest is promoted to production.
2. **Alert on application-level upload success rate, not 5xx.** The current alert cannot see any failure the service reports with a 200.
3. **Run at least one integration test against the real thumbnail generator** in the production image, so a missing runtime dependency fails the pipeline rather than the deploy.
4. **Audit other alerts for the same status-vs-outcome gap.** If this alert measured the wrong signal, others likely do too.
5. **Review why the first ticket sat 22 minutes before anyone noticed** ticket volume, and whether support ticket rate should page.