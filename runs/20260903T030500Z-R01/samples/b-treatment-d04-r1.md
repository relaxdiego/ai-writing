# Incident Postmortem: Image Upload Failure (2025-07-14)

**Duration:** 2025-07-14 09:12–11:48 UTC (2h 36m)
**Impact:** Image uploads failed for all users. Approximately 18,000 uploads failed. No data loss.

## Summary

Version 4.7.0 of `media-service` changed the thumbnail generator to shell out to an `ImageMagick` binary that was not present in the production container image. Every upload failed from the moment the deploy landed. The failure returned HTTP 200 with an error body, so the 5xx-rate alert never fired, and the outage was discovered 49 minutes later through customer support tickets rather than monitoring.

## Timeline (UTC)

| Time | Event |
|---|---|
| 09:12 | `media-service` v4.7.0 deployed |
| 09:14 | Upload error rate rises from 0.2% to 100%. No alert fires — the alert measures 5xx rate, and the service returns 200 with an error body |
| 09:41 | First customer support ticket |
| 10:03 | Engineer notices ticket volume, begins investigating |
| 10:20 | Root cause identified: v4.7.0 requires an `ImageMagick` binary absent from the production container image |
| 10:31 | Rollback started |
| 10:44 | Rollback complete; uploads recover |
| 11:48 | Backlog of retried uploads drains; incident closed |

Time to detection: 51 minutes. Time to mitigation: 92 minutes. Time to full recovery: 2h 36m.

## Root cause

The thumbnail generator in v4.7.0 invokes an `ImageMagick` binary. That binary exists in the image used by CI but not in the image used in production, because the two are built from different Dockerfiles. The dependency was therefore satisfied everywhere it was tested and unsatisfied everywhere it ran.

## Contributing factors

**Divergent build definitions.** Production and CI container images are built from separate Dockerfiles. Any dependency added to one is invisible to the other, so CI cannot verify that production has what the code needs.

**Mocked integration tests.** The integration suite mocks the thumbnail generator, so no test exercised the real binary invocation. A test that ran the generator for real would have failed in CI even with the divergent Dockerfiles, provided CI used the production image.

**Alert measured the wrong signal.** The upload alert was defined on HTTP 5xx rate. Because failures were returned as 200 with an error body, a 100% failure rate produced no change in the monitored signal. Detection fell back to customer reports.

## What went well

Once investigation began, root cause was identified in 17 minutes and rollback completed 24 minutes after that. Failed uploads were retried and drained without data loss.

## Action items

| Action | Rationale |
|---|---|
| Build production and CI images from a single Dockerfile | Removes the class of defect where CI validates a different runtime than production |
| Add an integration test that exercises the real thumbnail generator against the production image | Catches missing runtime dependencies before deploy |
| Redefine upload alerting on application-level success rate, not HTTP status | The current alert is blind to any failure returned as a 200 |
| Audit remaining alerts for the same status-vs-outcome mismatch | This alert is unlikely to be the only one defined on transport-level signals |
| Have the service return a 5xx for upload failures | Aligns HTTP semantics with actual outcome; defense in depth alongside the alerting change |