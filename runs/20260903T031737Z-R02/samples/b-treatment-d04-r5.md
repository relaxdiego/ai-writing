# Incident Postmortem: Image Upload Failure (2025-07-14)

## Summary

Between 09:12 and 11:48 UTC on 2025-07-14, image uploads failed for all users following the deployment of `media-service` v4.7.0. The release changed the thumbnail generator to shell out to an `ImageMagick` binary that was not present in the production container image, so every upload failed at the thumbnailing step. Roughly 18,000 uploads failed over the 2h36m window. No data was lost; failed uploads were rejected outright rather than partially written, and clients retried successfully once service was restored.

## Impact

All upload traffic was affected from 09:14 onward — the error rate went from a baseline of 0.2% to 100% within two minutes of the deploy. Because the service returned HTTP 200 with an error body, clients saw failures but our monitoring did not, and the failure was invisible to us until customers reported it. The first support ticket arrived at 09:41, and it took another 22 minutes of accumulating ticket volume before an engineer began investigating at 10:03. Nearly an hour of total outage elapsed before anyone at the company knew there was an incident.

## Timeline (UTC)

| Time | Event |
|---|---|
| 09:12 | `media-service` v4.7.0 deployed to production |
| 09:14 | Upload error rate reaches 100%; no alert fires |
| 09:41 | First customer support ticket received |
| 10:03 | Engineer notices ticket volume, begins investigating |
| 10:20 | Root cause identified: v4.7.0 requires an `ImageMagick` binary absent from the production image |
| 10:31 | Rollback to prior version started |
| 10:44 | Rollback complete; uploads recover |
| 11:48 | Backlog of retried uploads drains; incident closed |

## Root cause

v4.7.0 replaced the in-process thumbnail generation path with a call to an external `ImageMagick` binary. That binary exists in the CI build environment but not in the production container image, and nothing in the release pipeline was positioned to catch the difference. The gap traces back to the container image being built from a Dockerfile distinct from the one CI uses, so a dependency added for CI is not automatically a dependency present in production — the two images can drift arbitrarily far apart with no signal that they have. Compounding this, the integration test suite mocks the thumbnail generator entirely, which means the code path that invokes the binary is never exercised against a real environment in any pre-production stage. The change therefore passed every gate we have while being broken in the only environment that matters.

## Why detection took 49 minutes

The upload alert measured HTTP 5xx rate, but the failing code path caught the exception and returned HTTP 200 with an error body in the response payload. From the load balancer's perspective the service was perfectly healthy at 100% failure. This is the more expensive of the two defects: the missing binary would have been a five-minute rollback had we been paged at 09:14, and instead it became a two-and-a-half-hour outage discovered by customers.

## Contributing factors

1. **Divergent Dockerfiles.** The production container image is built from a different Dockerfile than the one used in CI, so runtime dependencies validated in CI carry no guarantee in production.
2. **Mocked integration tests.** The integration suite mocks the thumbnail generator, leaving the external-binary invocation untested end to end.
3. **Status-code-based alerting.** Alerting measured transport-level status rather than application-level success, making a total functional outage indistinguishable from healthy traffic.

## Action items

| Action | Rationale |
|---|---|
| Alert on application-level upload success rate, not HTTP status | Directly addresses the 49-minute detection gap; would have paged at ~09:15 |
| Build production and CI images from a single Dockerfile | Eliminates the drift class that allowed this dependency to go missing |
| Add a smoke test that runs a real thumbnail generation against the production image before promotion | Catches missing runtime dependencies that mocked tests cannot |
| Audit remaining alerts for status-code-only conditions | This failure mode likely exists on other services |
| Return non-2xx status codes for server-side upload failures | Restores the correctness of transport-level monitoring generally |

## What went well

Once investigation began, diagnosis was fast — 17 minutes from first look to identified root cause, and 11 minutes from there to rollback initiation. The rollback itself was clean and uploads recovered immediately. Client-side retry behavior worked as designed, so the failed uploads drained without customer intervention and without data loss.