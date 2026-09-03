# Incident postmortem: total image upload failure following media-service v4.7.0

## Summary

Between 09:12 and 11:48 UTC on 14 July 2025, image uploads failed for every user of the service. The failure began two minutes after `media-service` v4.7.0 was deployed and persisted until a rollback completed at 10:44, with the remaining 64 minutes spent draining a backlog of client retries. Approximately 18,000 uploads failed during the window. No data was lost: uploads either failed before any object was written or were retried successfully once the service recovered.

The dominant cost of this incident was detection. The broken deploy was identified and rolled back within 24 minutes of an engineer beginning to investigate, but 111 minutes elapsed between the failure starting and that investigation starting, because no alert fired and the first signal to reach engineering was customer support ticket volume.

## Timeline (UTC)

- **09:12** — `media-service` v4.7.0 deployed to production.
- **09:14** — Upload error rate rises from 0.2% to 100%. No alert fires; the alert is defined on HTTP 5xx rate, and the failing requests return HTTP 200 with an error payload in the body.
- **09:41** — First customer support ticket filed.
- **10:03** — An engineer notices the volume of incoming tickets and begins investigating.
- **10:20** — Cause identified: v4.7.0 changed the thumbnail generator to shell out to an `ImageMagick` binary that is not present in the production container image.
- **10:31** — Rollback to v4.6.x begins.
- **10:44** — Rollback complete; uploads recover.
- **11:48** — Backlog of retried uploads drains; incident closed.

## What happened

Version 4.7.0 reimplemented thumbnail generation to invoke `ImageMagick` as an external binary rather than using the previous in-process library. The binary was added to the CI Dockerfile, where the change was validated, but the production container image is built from a separate Dockerfile that was not updated. Every upload therefore reached the thumbnail step, failed to execute the missing binary, and returned an error to the client.

That error was returned as HTTP 200 with a failure code in the response body, which is the service's existing convention for upload results. The paging alert measured the proportion of 5xx responses, so a complete outage of the upload path produced no change in the signal the alert watched. The graph the alert was built on stayed flat through the entire outage while the application-level success rate sat at zero.

The change also passed the integration suite, which mocks the thumbnail generator rather than executing it. The mock returns a valid thumbnail regardless of what the real code path would do, so no test in the pipeline exercised the new binary invocation, and no test ran against the artifact that would actually be deployed.

## Contributing factors

Three independent gaps had to line up for a missing binary to become a 2h36m total outage.

The production container image is built from a different Dockerfile than the one CI uses. This means CI validates an artifact that is not the artifact shipped to production, and any dependency added to one file silently diverges from the other. The `ImageMagick` addition is a mild instance of a general problem: nothing in the pipeline can catch a divergence of this kind, because the two images are never compared and the production image is never tested.

The integration suite mocks the thumbnail generator. Mocking is defensible for a component that is slow or external, but the thumbnail generator is neither; it is core to the upload path, and mocking it removed the only test that would have executed the new code. The suite reported a green build for a service whose primary function was broken.

The alert measured HTTP status rather than application-level success. The service deliberately returns 200 for failed uploads, so status code is not a proxy for whether uploads work, and the alert was measuring a quantity that could not move during this class of failure. The consequence was that detection fell back to customer support, which added 49 minutes before the first ticket and another 22 before anyone in engineering read it.

## Action items

1. **Build the production image from the CI Dockerfile.** Consolidate to a single Dockerfile, or, if the two must differ, add a build-time check that fails when their installed-package sets diverge. Owner: Platform. Priority: high.
2. **Add a post-deploy smoke test that uploads a real image through the deployed artifact** and asserts a thumbnail is produced. This runs against the production image and would have caught the failure before it reached users. Owner: Media. Priority: high.
3. **Re-point upload alerting at application-level success rate**, parsing the response body rather than the status code, and page when the success rate drops below 95% over five minutes. Audit other alerts on services that return 200 on failure. Owner: Media, with SRE review. Priority: high.
4. **Un-mock the thumbnail generator in the integration suite**, running the real binary against a small fixture set. Owner: Media. Priority: medium.
5. **Route support ticket volume spikes to the on-call channel.** Support held a clear signal for 22 minutes with no automatic path to engineering. Owner: Support Ops. Priority: medium.

## What went well

Once an engineer was looking at the problem, diagnosis took 17 minutes and rollback took a further 13. The rollback itself was clean and required no manual data repair. Client retry behaviour meant that the 18,000 failed uploads were largely resubmitted without user intervention, which is why the incident produced no data loss despite a complete outage of the write path.