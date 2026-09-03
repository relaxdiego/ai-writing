# Incident Postmortem: Image Upload Failure, 2025-07-14

## Summary

Between 09:12 and 11:48 UTC on 2025-07-14, image uploads failed for all users of the platform, a total outage of the upload path lasting 2 hours and 36 minutes. Roughly 18,000 upload attempts failed during the window. No data was lost: uploads that failed were rejected outright rather than partially written, and the client retry backlog drained successfully once service was restored.

The cause was a deploy of `media-service` v4.7.0, which changed the thumbnail generator to shell out to an `ImageMagick` binary that is not present in the production container image. Every upload therefore failed at the thumbnailing step. The failure went undetected by monitoring for 51 minutes and undiagnosed for 68 minutes after that, because the service returned HTTP 200 with an error body and our alerting measured only the 5xx rate.

## Timeline (UTC)

At 09:12 the v4.7.0 deploy went out. Within two minutes the upload error rate moved from a baseline of 0.2% to 100%, and no alert fired. The first customer support ticket arrived at 09:41, and it was not until 10:03 that an engineer noticed the rising ticket volume and began investigating. The missing binary was identified at 10:20, a rollback started at 10:31 and completed at 10:44, at which point uploads recovered immediately. The backlog of retried uploads drained by 11:48 and the incident was closed.

Two intervals in that sequence are worth naming. The 49 minutes from 09:14 to 10:03 is pure detection latency: the system was fully broken and nothing in our tooling said so, so we learned about it from customers. The 17 minutes from 10:03 to 10:20 is diagnosis, which is respectable given that the engineer started from "tickets are up" rather than from an alert pointing at a specific service and a specific deploy.

## Root cause and contributing factors

The direct cause is straightforward: v4.7.0 introduced a runtime dependency on an `ImageMagick` binary that the production container image does not contain. Three separate gaps let that dependency reach production and stay there.

The production container image is built from a different Dockerfile than the one used in CI. This is the core defect. It means CI cannot, even in principle, verify that the artifact we ship will run, because CI never builds that artifact. Any divergence between the two files is an untested difference, and here the divergence was exactly the package that the new code required.

The integration test suite mocks the thumbnail generator. The mock made the test suite pass against a code path that could not execute in any real environment. A test that stands in for the component whose behaviour changed will report success no matter what that component now needs.

The alert measured HTTP status rather than application-level success. The service returned 200 responses carrying error bodies, so from the monitoring system's point of view the service was perfectly healthy while failing every request it received. This is why we were told about the outage by a customer support queue rather than by a page.

## Action items

The highest-value fix is to build the production image in CI and deploy that exact artifact, retiring the second Dockerfile entirely. Until the two files are one file, every deploy carries this class of risk regardless of what else we change.

Alongside that, we should add a smoke test that runs against the real built image and performs an end-to-end upload, including thumbnail generation, with no mocks. It should run as a deploy gate. Had such a test existed, it would have caught this specific failure before any traffic reached the new version.

We should also replace the 5xx-rate alert on the upload path with one measuring application-level upload success, and audit our other alerts for the same assumption that HTTP status reflects operational health. Given how easily a 200-with-error-body slipped past us here, it is unlikely this is the only place we make that assumption.

Finally, a smaller process point: support ticket volume was the true first signal at 09:41, twenty-two minutes before an engineer acted on it. A threshold alert on ticket rate would not replace proper instrumentation, but it would have narrowed the detection gap while the deeper fixes are in progress.