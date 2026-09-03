# Incident Postmortem: Image Upload Failure (2025-07-14)

## Summary

Between 09:12 and 11:48 UTC on 2025-07-14, image uploads failed for all users of the platform, a window of 2 hours and 36 minutes during which roughly 18,000 upload attempts were rejected. The cause was a deploy of `media-service` v4.7.0 that introduced a dependency on an `ImageMagick` binary absent from the production container image, so every thumbnail generation call failed the moment the new version took traffic. No data was lost; uploads that clients retried after recovery were accepted normally, and the incident closed once that retry backlog drained.

## Timeline (UTC)

| Time | Event |
| --- | --- |
| 09:12 | `media-service` v4.7.0 deployed to production |
| 09:14 | Upload error rate rises from 0.2% to 100%; no alert fires |
| 09:41 | First customer support ticket received |
| 10:03 | Engineer notices ticket volume and begins investigating |
| 10:20 | Root cause identified: v4.7.0 requires an `ImageMagick` binary missing from the production image |
| 10:31 | Rollback started |
| 10:44 | Rollback complete; uploads recover |
| 11:48 | Retried-upload backlog drains; incident closed |

## What happened

The failure itself was total and immediate: within two minutes of the deploy, the error rate went from 0.2% to 100%. What turned a two-minute failure into a two-and-a-half-hour incident was that nothing told us about it. The new thumbnail generator returned an error body inside an HTTP 200 response, and our upload alert was defined on 5xx rate, so from the monitoring system's perspective the service was healthy and serving traffic successfully for the entire outage. The first signal that anything was wrong arrived 27 minutes in, through customer support, and it took another 22 minutes for ticket volume to accumulate enough that an engineer noticed it and began looking. Detection consumed 51 of the 92 minutes of user-visible failure; once an engineer was actually investigating, diagnosis took 17 minutes and the rollback itself took 13.

The bug reached production because two separate safeguards each had a blind spot that the other might otherwise have covered. The production container image is built from a different Dockerfile than the one CI uses, so a dependency added to the CI image does not imply the same dependency exists in the image that actually runs. That divergence would normally be caught by integration tests exercising the real code path, but the integration suite mocks the thumbnail generator, meaning no test in the pipeline ever invoked the binary that was missing. The change passed every gate we have while being broken in the only environment that matters.

## Contributing factors

- **Divergent Dockerfiles.** The production image and the CI image are built from separate Dockerfiles with no mechanism keeping their system-level dependencies in sync, so CI cannot attest to what production will contain.
- **Mocked integration tests.** The integration suite mocks the thumbnail generator, so the code path that depends on `ImageMagick` is never exercised against a real binary anywhere in the pipeline.
- **Alerting on transport status rather than application outcome.** The upload alert measured HTTP 5xx rate. Because the service returned 200 with an error body, a complete outage was invisible to monitoring for its entire duration.

## Action items

1. **Alert on application-level upload success rate**, not HTTP status, with a threshold that would have fired within minutes at 09:14. This is the highest-value fix: it does not prevent the class of bug, but it collapses the 51-minute detection gap regardless of what causes the next failure.
2. **Build production and CI images from a single Dockerfile**, or derive both from a shared base that pins system dependencies in one place, so a dependency present in test is present in production by construction.
3. **Run at least one integration test against the real thumbnail generator** in the production image, so a missing binary fails the pipeline rather than the deploy.
4. **Audit remaining alerts for the same status-versus-outcome mismatch.** The alert gap here is unlikely to be unique to uploads; any endpoint that can return 200 with an error body has the same hole.
5. **Add a post-deploy health check on key user-facing success metrics** that gates or automatically reverts a rollout when they degrade sharply, which would have caught this at 09:14 without human involvement.