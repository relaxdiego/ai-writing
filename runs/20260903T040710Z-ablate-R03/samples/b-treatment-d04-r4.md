# Incident postmortem: image upload failure, 2025-07-14

## Summary

Between 09:12 and 11:48 UTC on 2025-07-14, a total of 2 hours and 36 minutes, image uploads failed for every user of the platform. Roughly 18,000 upload attempts failed during the window. No data was lost: uploads that failed were rejected outright rather than partially written, and clients retried successfully once the service recovered.

The cause was a deploy of `media-service` v4.7.0, which changed the thumbnail generator to shell out to an `ImageMagick` binary that is not present in the production container image. Every upload therefore failed at the thumbnailing step. The failure was total from the moment the deploy landed, but it went undetected by monitoring for 49 minutes and unattended for 51, because the service returned HTTP 200 with an error body and the paging alert was defined on 5xx rate.

## Timeline (UTC)

- **09:12** — `media-service` v4.7.0 deploys to production.
- **09:14** — Upload error rate rises from 0.2% to 100%. No alert fires; the alert measures 5xx rate and the service is returning 200 responses carrying an error body.
- **09:41** — First customer support ticket arrives.
- **10:03** — An engineer notices the ticket volume and begins investigating.
- **10:20** — Root cause identified: v4.7.0's thumbnail generator requires an `ImageMagick` binary absent from the production container image.
- **10:31** — Rollback to the previous version begins.
- **10:44** — Rollback completes and uploads recover.
- **11:48** — The backlog of retried uploads drains and the incident is closed.

## What went wrong

Three independent gaps had to line up for a missing binary to become a two-and-a-half-hour total outage, and each of them is worth treating as a defect in its own right.

The production container image is built from a different Dockerfile than the one CI uses. This means the artifact we test is not the artifact we ship, and any dependency added to the CI image is invisibly absent from production until something at runtime reaches for it. The new `ImageMagick` dependency was satisfied in CI and unsatisfied in production, and nothing in the pipeline was capable of noticing the difference.

The integration test suite mocks the thumbnail generator. Mocking the component whose behaviour changed meant the test suite exercised the new code path against a stand-in that has no external dependencies at all, so a passing suite carried no information about whether thumbnailing would work. A change to the generator's execution model is precisely the change a mock cannot evaluate.

The paging alert measured HTTP status rather than application-level success. Because the upload endpoint signals failure in the response body while returning 200, a complete outage was indistinguishable from healthy traffic as far as the alert was concerned. Detection fell back to customers filing tickets, which cost 49 minutes, and then to an engineer happening to notice the ticket volume, which cost another 22. Once someone was actually looking at the problem, diagnosis took 17 minutes and remediation 24, so the response was fast and the detection was not.

## Corrective actions

The container image problem is the one that most needs to be closed first: production should ship the artifact CI built, rather than rebuilding from a second Dockerfile. Until the two are unified, any dependency change carries this same risk.

Alerting on uploads should move to application-level success rate, measured from the outcome recorded in the response body rather than the status code. Separately, the upload endpoint returning 200 on server-side failure is itself a bug worth fixing, since it misleads clients, proxies, and retry logic in the same way it misled the alert.

Finally, the integration suite needs at least one path that runs the real thumbnail generator against the real image, ideally as a post-deploy smoke test against a canary instance, so that a missing runtime dependency fails the deploy rather than the users.