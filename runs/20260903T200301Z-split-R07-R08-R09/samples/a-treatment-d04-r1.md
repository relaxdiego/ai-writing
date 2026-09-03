# Incident postmortem: image upload failure following `media-service` v4.7.0

**Date:** 2025-07-14, 09:12–11:48 UTC (2h36m)
**Impact:** Image uploads failed for all users. Roughly 18,000 uploads failed. No data was lost.

## Summary

A deploy of `media-service` v4.7.0 introduced a thumbnail generator that shells out to an `ImageMagick` binary. That binary is not present in the production container image, so every upload failed from the moment the deploy landed. The failure was invisible to monitoring because the service returned HTTP 200 with an error body, and the alert measured 5xx rate. The outage was found through customer support tickets 51 minutes after it began, and was resolved by rolling back to the previous version.

Uploads were failing for users between 09:12 and 10:44, a window of 1h32m. The remaining hour was the retry backlog draining, during which uploads were succeeding.

## Timeline

| Time (UTC) | Event |
| --- | --- |
| 09:12 | `media-service` v4.7.0 deployed to production |
| 09:14 | Upload error rate rises from 0.2% to 100%. No alert fires: the alert is on 5xx rate, and the service returns 200 with an error body |
| 09:41 | First customer support ticket |
| 10:03 | An engineer notices the ticket volume and begins investigating |
| 10:20 | Cause identified: v4.7.0 requires an `ImageMagick` binary absent from the production container image |
| 10:31 | Rollback started |
| 10:44 | Rollback complete; uploads recover |
| 11:48 | Retry backlog drains; incident closed |

## Contributing factors

Three independent gaps had to line up for this to reach production and stay there for two and a half hours.

- **The production container image is built from a different Dockerfile than the one CI uses.** A dependency added for CI's image is not thereby added for production's, and nothing in the pipeline compares the two. This is what allowed a missing binary to be a deploy-time surprise rather than a build-time failure.
- **The integration test suite mocks the thumbnail generator.** The tests exercised the calling code and passed; the one thing that changed in v4.7.0, the generator's runtime requirements, was the thing the tests replaced with a stub.
- **The upload alert measured HTTP status rather than application-level success.** A handler that catches its own errors and returns 200 is invisible to a 5xx-rate alert. Detection therefore fell to customers, which cost 49 minutes between total failure and the first human looking at it.

## What went well

The rollback was fast once the cause was known: 11 minutes from diagnosis to recovery. No uploads were lost, because clients retried and the backlog drained cleanly.

## Action items

These follow from the contributing factors above. Owners and target dates still need to be assigned; that is the one part of this document that cannot be filled in from the incident record.

1. **Alert on application-level upload success rate, not HTTP status.** This is the highest-value item: with it in place, the same bug would have paged someone at 09:14 rather than surfacing in a support queue at 09:41.
2. **Build production and CI images from a single Dockerfile,** or, failing that, add a pipeline check that fails when the two diverge in installed packages.
3. **Add a smoke test that runs the thumbnail generator unmocked against the production image** as a post-deploy gate, so a missing runtime dependency fails the deploy instead of the user.
4. **Audit other handlers for error responses returned with 200 status,** since the alerting gap this exposed is unlikely to be confined to uploads.