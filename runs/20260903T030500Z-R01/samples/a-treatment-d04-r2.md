# Incident Postmortem: Image upload failure following `media-service` v4.7.0

**Date:** 2025-07-14
**Duration:** 09:12–11:48 UTC (2h 36m); user-visible failures 09:14–10:44 (1h 30m)
**Impact:** Image uploads failed for 100% of users. Roughly 18,000 uploads failed. No data loss.

## Summary

`media-service` v4.7.0 changed the thumbnail generator to shell out to an `ImageMagick` binary. That binary is not present in the production container image, so every upload failed immediately after the deploy. The service returned HTTP 200 with an error body, so the 5xx-rate alert never fired and the failure was invisible to monitoring. The problem was found only after support tickets accumulated. Rolling back to v4.6.x restored service.

## Timeline (UTC)

| Time | Event |
|---|---|
| 09:12 | `media-service` v4.7.0 deployed to production |
| 09:14 | Upload error rate rises from 0.2% to 100%. No alert fires |
| 09:41 | First customer support ticket |
| 10:03 | An engineer notices the ticket volume and begins investigating |
| 10:20 | Cause identified: v4.7.0 requires an `ImageMagick` binary absent from the production image |
| 10:31 | Rollback started |
| 10:44 | Rollback complete; uploads recover |
| 11:48 | Backlog of retried uploads drains; incident closed |

Detection took 49 minutes from onset to a human investigating, and it came from customers rather than from monitoring. Once someone was looking, diagnosis took 17 minutes and remediation 24 more.

## Root cause

v4.7.0 introduced a runtime dependency on the `ImageMagick` binary. The production container image is built from a different Dockerfile than the one used in CI, and only the CI image had the binary installed. The dependency was therefore satisfied everywhere the code was tested and unsatisfied in the only environment that mattered.

The failure was total and immediate rather than partial: every upload path reaches the thumbnail generator, so the missing binary took out the whole feature the moment the deploy landed.

## Why it wasn't caught before production

**CI and production build from different Dockerfiles.** This makes CI's environment a poor predictor of production's. Any dependency added to one image without the other produces exactly this class of failure, and nothing in the pipeline compares them.

**The integration test suite mocks the thumbnail generator.** The tests exercised the calling code and asserted on a stubbed response, so they passed against a binary that was never invoked. The mock removed the only test that could have detected the missing dependency.

## Why it wasn't detected in production

The alert measured HTTP status codes. The service returned 200 with an error payload, so from the alert's perspective the service was healthy at 100% failure. This is a monitoring design gap rather than a tuning problem: the signal being measured (transport-level status) is not the signal that matters (application-level upload success). Nothing would have made this alert fire.

The 49-minute gap between onset and investigation is a direct consequence. The first real signal was the support queue, which is slow by nature and depends on someone noticing volume rather than being paged.

## What went well

Once the failure was being investigated, diagnosis and rollback were quick — 41 minutes from engineer engagement to full recovery, with no debate about whether to roll back. Client-side retries preserved the failed uploads; the backlog drained on its own and no user data was lost.

## Action items

1. **Build production and CI images from the same Dockerfile.** This is the fix that would have prevented the incident outright. Until it lands, add a pipeline check that fails if the two Dockerfiles diverge.
2. **Alert on application-level upload success rate, not HTTP status.** Any endpoint that can return 200 with an error body needs a success metric emitted by the application itself. Audit other services for the same pattern.
3. **Replace the thumbnail generator mock with a test that runs the real binary in the production image.** More generally, integration tests for code with external binary dependencies should execute against the deployed image rather than a stub.
4. **Add a post-deploy canary on upload success** so a 100% failure rate pages within minutes of a deploy rather than surfacing through support.

Items 1 and 2 are the ones that matter. Item 1 closes the cause; item 2 closes the detection gap, which turned a two-minute rollback into a ninety-minute outage.