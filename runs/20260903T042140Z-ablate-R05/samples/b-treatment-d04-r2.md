# Incident postmortem: total image upload failure

**Date:** 2025-07-14, 09:12–11:48 UTC (2h36m)
**Impact:** Image uploads failed for all users. Roughly 18,000 uploads failed. No data was lost.

## Summary

A routine deploy of `media-service` v4.7.0 introduced a dependency on the `ImageMagick` binary, which is not present in the production container image. Every upload that reached the thumbnail generation step failed. The service returned HTTP 200 with an error body, so the alert on 5xx rate never fired, and the failure was invisible to monitoring for 49 minutes until the first customer support ticket arrived. Detection ultimately depended on a person noticing an unusual volume of tickets. Once an engineer began investigating, diagnosis took 17 minutes and the rollback restored service 24 minutes after that. The remaining hour was spent draining the backlog of client-side retries.

## Timeline

- **09:12** — `media-service` v4.7.0 deploys to production.
- **09:14** — Upload error rate rises from 0.2% to 100%. No alert fires; the alert measures 5xx responses and the service is returning 200 with an error body.
- **09:41** — First customer support ticket.
- **10:03** — An engineer notices the ticket volume and begins investigating.
- **10:20** — Cause identified: v4.7.0 changed the thumbnail generator to shell out to `ImageMagick`, which is absent from the production container image.
- **10:31** — Rollback to v4.6.x begins.
- **10:44** — Rollback complete; uploads recover.
- **11:48** — Backlog of retried uploads drains. Incident closed.

## Root cause

The v4.7.0 thumbnail generator invokes an `ImageMagick` binary at runtime. That binary exists in the image CI builds and tests against, but production containers are built from a separate Dockerfile that was never updated to include it. The divergence meant the change passed every gate that ran before deploy and failed on the first request it served in production.

## Contributing factors

Three independent gaps had to line up for this to become a two-hour outage, and each one is worth treating separately.

The production container image is built from a different Dockerfile than the one used in CI. This is the proximate reason the missing dependency was not caught: CI validated an artifact that is not the artifact we ship, so a passing build carried no information about whether production would work.

The integration test suite mocks the thumbnail generator. Even had CI used the production image, the tests would not have exercised the code path that shells out to the binary. The mock was presumably introduced to keep tests fast and hermetic, but it removed coverage from exactly the boundary where this class of failure occurs.

The alert measured HTTP status rather than application-level success. The service reported failures as 200 responses carrying an error body, a pattern that is common enough in our API surface that the monitoring gap likely extends well beyond uploads. This factor is the one that turned a bad deploy into a long incident: the technical fault lasted 90 minutes, but roughly 50 of those minutes were spent with nobody aware anything was wrong.

## What we are changing

The most valuable fix is the alerting one, because it shortens every future incident of this shape regardless of cause. We will alert on application-level upload success rate rather than status code, with a threshold sensitive enough to fire within a few minutes of a 100% failure, and audit other services for endpoints that report failure inside a 200.

Second, the two Dockerfiles need to be reduced to one, with CI building the same image that is promoted to production. If a single Dockerfile is not achievable quickly, an interim check that diffs the installed package sets between the two images and fails the build on divergence would have caught this specific change.

Third, the integration suite should exercise thumbnail generation against the real binary in the real image, at least in one end-to-end test. A single unmocked upload test running against the production artifact would have failed this deploy in CI.

Finally, this deploy served 100% failures for 90 minutes with no automated signal. A post-deploy smoke test that uploads an image and verifies the resulting thumbnail, gating promotion or triggering automatic rollback, would have bounded the impact to a few minutes independent of whether anyone was watching a dashboard.

## What went well

Once investigation began, diagnosis was fast: 17 minutes from first look to identified cause on a failure mode with no useful alerting and a misleading status code. The rollback path worked as intended and restored service in 13 minutes. Client retries meant no uploads were permanently lost, though they also produced the backlog that extended the incident by an hour after service recovered.