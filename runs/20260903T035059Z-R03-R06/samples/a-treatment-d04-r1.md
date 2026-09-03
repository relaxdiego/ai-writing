# Incident postmortem: image uploads unavailable, 2025-07-14

## Summary

A deploy of `media-service` v4.7.0 at 09:12 UTC broke thumbnail generation, and image uploads failed for every user until a rollback completed at 10:44. Approximately 18,000 uploads failed over the ninety minutes of customer-facing failure, an average of about 200 per minute. The incident remained open until 11:48 while the backlog of client retries drained, giving a total duration of two hours and thirty-six minutes. No data was lost; uploads failed outright rather than partially, and clients that retried after 10:44 succeeded.

## Timeline (UTC)

- 09:12 — v4.7.0 of `media-service` deploys.
- 09:14 — Upload error rate rises from 0.2% to 100%. No alert fires: the alert is defined on 5xx rate, and the service returns HTTP 200 with an error body.
- 09:41 — First customer support ticket.
- 10:03 — An engineer notices the ticket volume and begins investigating. Detection latency from onset: 49 minutes.
- 10:20 — Cause identified. v4.7.0 changed the thumbnail generator to invoke an `ImageMagick` binary that is not present in the production container image.
- 10:31 — Rollback started.
- 10:44 — Rollback complete; uploads recover.
- 11:48 — Retry backlog drains; incident closed.

## Analysis

The proximate cause is straightforward. Version 4.7.0 changed the thumbnail generator to shell out to an `ImageMagick` binary, and the production container image does not contain that binary. Every upload reached thumbnail generation and failed there, which is why the error rate went to 100% rather than to some fraction. The upload handler caught the generation failure and returned HTTP 200 with an error body, so from the outside every request looked like a successful one carrying a failure payload.

That response shape is what cost us the first 49 minutes. The upload alert measured 5xx rate, which stayed flat at zero throughout, and nothing else in the monitoring stack examined application-level outcomes. Detection came from customers instead: the first ticket arrived at 09:41, and ticket volume was noticed at 10:03. Response after that point was fast, with 17 minutes to diagnosis, 11 more to begin the rollback, and 13 for the rollback to complete. Of the ninety minutes users spent unable to upload, roughly 55% elapsed before anyone knew.

Two independent gaps let the change reach production. First, the production container image is built from a different Dockerfile than the one CI uses, so CI never exercised the artifact that actually ships; `ImageMagick` was present in the CI build environment and absent in the production one, and no stage compared them. Second, the integration test suite mocks the thumbnail generator, so no test in any environment invoked the real code path that would have discovered the missing binary. Either gap alone would likely have been survivable. An integration test against the real generator would have failed in CI despite the Dockerfile divergence, and the mock would have been harmless if CI had built and tested the shipping image.

The final hour of the incident is a separate effect worth recording: uploads recovered at 10:44, but client retries had accumulated for ninety minutes and took another 64 minutes to drain. Users who retried during that window experienced continued latency after the underlying fault was gone.

## Corrective actions

The notes do not name owners or target dates, so those fields are left blank below and need filling in before this is circulated.

1. Build the production container image in CI and run the test suite against that image. Remove the second Dockerfile so there is one build path rather than two that can drift.
2. Change the upload endpoint to return 5xx when the upload fails. Returning 200 with an error body is a defect in its own right, since it defeats both alerting and any client or proxy retry logic that keys on status.
3. Alert on application-level upload success rate, independent of HTTP status, so that a future failure of this shape pages regardless of what the endpoint returns.
4. Add at least one integration test that exercises the real thumbnail generator, including its external binary dependency, against the shipping image. Keep the mock for unit tests only.
5. Given that the error rate reached 100% within two minutes of the deploy, wire the success-rate signal from item 3 into an automatic post-deploy rollback. With that signal in place, an incident of this shape would be bounded to a few minutes rather than ninety.