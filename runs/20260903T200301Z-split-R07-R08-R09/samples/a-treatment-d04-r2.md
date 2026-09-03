# Incident postmortem: image uploads unavailable, 14 July 2025

## Summary

All image uploads failed for 2 hours 36 minutes, from 09:12 to 11:48 UTC, affecting every user who attempted an upload during that window. Roughly 18,000 uploads failed. No data was lost; uploads failed during thumbnail generation, before anything was written to permanent storage, and the client retry backlog drained successfully once the service recovered.

The trigger was the deploy of `media-service` v4.7.0, which changed the thumbnail generator to invoke an `ImageMagick` binary that is not present in the production container image. Every upload therefore failed at the thumbnailing step. Recovery came from a rollback to the previous version.

## Timeline

All times UTC.

| Time | Event |
|---|---|
| 09:12 | `media-service` v4.7.0 deployed to production |
| 09:14 | Upload error rate rises from 0.2% to 100%. No alert fires |
| 09:41 | First customer support ticket |
| 10:03 | Engineer notices ticket volume and begins investigating |
| 10:20 | Missing `ImageMagick` binary identified as the cause |
| 10:31 | Rollback started |
| 10:44 | Rollback complete; uploads recover |
| 11:48 | Retry backlog drains; incident closed |

## What broke

v4.7.0 replaced the in-process thumbnail path with one that shells out to `ImageMagick`. The production container image has no such binary, so the call failed on every upload. The failure was caught and converted into an application-level error response rather than propagating as an unhandled exception, and the service returned HTTP 200 with an error body describing the failure.

That response shape is why detection took 49 minutes. The upload alert was defined on 5xx rate, and the 5xx rate never moved: from the monitoring system's perspective the service was healthy and serving traffic normally throughout a total outage of the feature. The first signal that reached anyone was customer support ticket volume, 27 minutes after the failures began, and it took a further 22 minutes before an engineer connected the ticket pattern to a production fault. Once someone was actually looking, diagnosis took 17 minutes and the rollback 13.

## Contributing factors

- **Divergent build definitions.** The production container image is built from a different Dockerfile than the one CI uses. A dependency added to the CI image satisfies the test suite while leaving production without it, and nothing compares the two.
- **Integration tests mock the thumbnail generator.** The suite exercises the code path that calls the generator but never the generator itself, so a change to the generator's runtime requirements cannot fail a test.
- **The alert measured transport, not outcome.** Alerting on HTTP status assumes failures surface as 5xx. Any failure mode that returns 200 with an error body is invisible to it, and this service has such a mode by design.

Each of these was independently sufficient to let the defect through: the build divergence let it ship, the mocked test let it pass review, and the status-based alert let it run unnoticed for 49 minutes.

## Remediation

The following actions follow from the factors above. Owners and target dates are not in the incident notes and need to be assigned before this document is closed out.

1. Build the production image and the CI image from the same Dockerfile, or have CI run its tests against the production image directly.
2. Add at least one integration test that runs the real thumbnail generator against the production image, so missing runtime dependencies fail the build.
3. Redefine the upload alert on application-level success rate rather than HTTP status, and audit other alerts for the same assumption.
4. Add a post-deploy check on upload success rate that can trigger an automatic rollback, which would have cut the 90-minute time to recovery to a few minutes.

## What went well

The rollback itself was clean and fast: 13 minutes from decision to recovery, with no manual data repair needed. Client-side retry behaviour meant the 18,000 failed uploads were largely resubmitted without user intervention, and the hour spent draining that backlog was recovery work rather than continued impact.