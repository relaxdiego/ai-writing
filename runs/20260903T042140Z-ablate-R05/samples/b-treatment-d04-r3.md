# Incident Postmortem: Image Upload Failure, 14 July 2025

## Summary

Between 09:12 and 11:48 UTC on 14 July 2025, image uploads failed for every user of the platform. The failure was total for the 92 minutes before rollback and produced roughly 18,000 failed uploads; a further hour was spent draining the backlog of client retries. No data was lost, because the uploads failed before anything was written rather than partway through. The cause was a deploy of `media-service` v4.7.0, which introduced a dependency on an `ImageMagick` binary that the production container image does not contain.

The incident is notable less for the bug than for how long it stayed invisible. The regression was live within two minutes of the deploy and complete in its effect, yet no alert fired at any point, and the first signal reached an engineer 51 minutes later by way of the support queue.

## Timeline (UTC)

| Time | Event |
|---|---|
| 09:12 | `media-service` v4.7.0 deployed to production |
| 09:14 | Upload error rate rises from 0.2% to 100%; no alert fires |
| 09:41 | First customer support ticket opened |
| 10:03 | Engineer notices ticket volume and begins investigating |
| 10:20 | Missing `ImageMagick` binary identified as the cause |
| 10:31 | Rollback to previous version begins |
| 10:44 | Rollback complete; uploads recover |
| 11:48 | Retry backlog drains; incident closed |

## What happened

The thumbnail generator in v4.7.0 was rewritten to shell out to `ImageMagick`. That binary is present in the development and CI environments but absent from the production container image, so every thumbnail generation attempt failed at the point of process invocation. The upload handler caught the failure and returned it to the client as an error body carried inside an HTTP 200 response, which is the existing convention in that service for application-level errors.

That convention is what suppressed detection. The upload alert was defined against the 5xx rate, and the 5xx rate never moved, because the service was cheerfully returning 200 for every failed upload. From the monitoring system's perspective the service was healthy for the entire duration of a complete outage. Detection therefore fell to customers, who took 29 minutes to file the first ticket, and then to an engineer noticing that tickets were accumulating, which took another 22 minutes. Once someone was actually looking, diagnosis took 17 minutes and rollback took a further 24, both of which are reasonable; the 51 minutes before that are not.

## Contributing factors

Three things had to be true at once for this to reach production undetected. The production container image is built from a different Dockerfile than the one CI uses, so a dependency added to the CI image is not added to the shipped image and nothing in the build compares them. The integration test suite mocks the thumbnail generator, so the tests that would have exercised the new code path never invoked the binary and passed identically in both environments. And the alerting measured transport-layer status rather than application-level success, so a service that reports its own errors inside a 200 response is by construction unmonitorable by that alert.

Each of these is individually defensible and collectively they removed every layer that could have caught the problem: the build could not catch it, the tests would not catch it, and the alerts could not see it.

## Action items

The most important change is to alert on application-level upload success rate rather than HTTP status, since that gap is what turned a two-minute regression into a two-and-a-half-hour incident. This should be in place before any further change to `media-service`.

The two Dockerfiles should be unified so that CI builds and validates the same image that ships to production. If a genuine reason exists to keep them separate, the build should at minimum fail when the two diverge in their installed dependencies.

The integration suite should exercise the real thumbnail generator against the production image in at least one test, so that a missing runtime dependency surfaces as a test failure rather than a customer ticket. More broadly, mocking a component that has external binary dependencies removes exactly the failure mode that mocking cannot detect, and the suite should be reviewed for other places where this holds.

Finally, the practice of returning application errors inside HTTP 200 responses should be reconsidered for `media-service`. It is a defensible API design in isolation, but it interacts badly with monitoring that assumes otherwise, and the safer resolution is for failed uploads to return an appropriate 5xx.