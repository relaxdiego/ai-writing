# Incident postmortem: image upload failure, 2025-07-14

## Summary

Image uploads failed for all users for 92 minutes, and the incident was open for 2h36m in total (09:12 to 11:48 UTC). The immediate cause was the deploy of `media-service` v4.7.0, which changed the thumbnail generator to invoke an `ImageMagick` binary that is not present in the production container image. Roughly 18,000 uploads failed, about 200 per minute across the failure window. No data was lost: the service rejected uploads rather than accepting and storing them incorrectly, and retried uploads drained successfully after the rollback.

The more serious finding is that the outage was invisible to monitoring for its entire first hour. v4.7.0 returned HTTP 200 with an error body on failure, and the paging alert measured 5xx rate, so an error-rate jump from 0.2% to 100% produced no signal at all. Detection came from customer support ticket volume, 49 minutes after uploads started failing.

## Timeline

All times UTC. Elapsed is measured from the deploy.

| Time | Elapsed | Event |
|---|---|---|
| 09:12 | 0m | `media-service` v4.7.0 deployed to production |
| 09:14 | +2m | Upload error rate rises from 0.2% to 100%. No alert fires: the alert is on 5xx rate, and the service returns 200 with an error body |
| 09:41 | +29m | First customer support ticket |
| 10:03 | +51m | Engineer notices ticket volume and begins investigating |
| 10:20 | +68m | Cause identified: v4.7.0 requires an `ImageMagick` binary absent from the production image |
| 10:31 | +79m | Rollback started |
| 10:44 | +92m | Rollback complete; uploads recover |
| 11:48 | +156m | Retry backlog drains; incident closed |

## Root cause

v4.7.0 rewrote thumbnail generation to depend on an `ImageMagick` binary at runtime. That binary exists in the image CI builds but not in the image that ships to production, because the two are built from different Dockerfiles. Every upload therefore reached the thumbnail step and failed on a missing executable. Nothing in the pipeline could have caught this: the integration suite mocks the thumbnail generator, so the only test that exercises the dependency never touches the real one, and CI validates an artifact that is not the artifact deployed.

## Detection and response

Diagnosis and remediation were fast once anyone was looking. From the engineer opening the investigation to identifying the cause took 17 minutes, and the rollback itself took 13 minutes. Of the 92 minutes users spent unable to upload, 49 were spent with nobody aware that anything was wrong.

The detection gap has a single cause. The alert asked whether the HTTP layer was healthy, and the HTTP layer was healthy throughout: the service was up, responding, and returning 200 to every request it failed. Support ticket volume was the only working detector, and it is a slow one, with 27 minutes elapsing before the first ticket arrived and another 22 before the volume was noticed.

## Contributing factors

- The production container image is built from a different Dockerfile than the one used in CI, so CI never tests the artifact that ships.
- The integration test suite mocks the thumbnail generator, which removed the one component whose runtime dependencies changed from test coverage.
- The alert measured HTTP status rather than application-level success, and the failure mode returned 200, so the alert was structurally incapable of firing.

Each of these on its own would have been survivable. The Dockerfile divergence created the defect, the mocked test let it through review and CI, and the status-code alert kept it from being noticed for an hour.

## Action items

The notes do not record owners or priorities, so those need to be assigned before this is closed out.

- **Alert on application-level upload success rate.** The current 5xx alert should be supplemented by, or replaced with, one that measures whether uploads actually succeed.
- **Return an error status on server-side failure.** Returning 200 with an error body is a defect in its own right, independent of the alerting change: it breaks client retry logic, load balancer health signals, and every downstream consumer that trusts the status code.
- **Build the production image from the Dockerfile CI tests,** or otherwise make CI validate the exact artifact that deploys. A single Dockerfile is the simpler fix if nothing depends on the divergence; if something does, that dependency should be documented in this ticket.
- **Add an integration test that exercises the real thumbnail generator** inside the shipping image. Mocking is reasonable for the generator's logic, but at least one test needs to prove the binary is present and callable.
- **Scope whether a staged rollout is feasible for `media-service`.** A canary would have capped the blast radius at a fraction of users and given the error-rate difference something to be measured against. Whether this is practical depends on the current deploy tooling and needs assessment before it is committed to.