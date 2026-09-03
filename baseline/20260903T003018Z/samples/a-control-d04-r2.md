# Incident Postmortem: Total Image Upload Failure

**Date:** 2025-07-14
**Duration:** 09:12–11:48 UTC (2h 36m)
**Status:** Resolved
**Severity:** High — full loss of a core user-facing function

## Summary

A routine deploy of `media-service` v4.7.0 introduced a dependency on the `ImageMagick` binary, which is not present in the production container image. Thumbnail generation failed for every upload, and the service returned HTTP 200 with an error body. Image uploads failed for all users for 2h 36m. Roughly 18,000 uploads failed. No data was lost; affected users were able to retry successfully after recovery.

The failure was invisible to monitoring. It was detected by customer support ticket volume, 49 minutes after it began.

## Impact

- Image uploads failed for 100% of users from 09:14 to 10:44 UTC.
- Approximately 18,000 upload attempts failed.
- No data loss. Uploads were rejected outright rather than partially written.
- A backlog of client-side retries took a further 64 minutes to drain after recovery, during which upload latency was elevated.

## Timeline (UTC)

| Time | Event |
|---|---|
| 09:12 | `media-service` v4.7.0 deployed to production |
| 09:14 | Upload error rate rises from 0.2% to 100%. No alert fires |
| 09:41 | First customer support ticket filed |
| 10:03 | Engineer notices ticket volume and begins investigating |
| 10:20 | Root cause identified: v4.7.0 requires `ImageMagick`, absent from the production image |
| 10:31 | Rollback to v4.6.x started |
| 10:44 | Rollback complete; uploads recover |
| 11:48 | Retry backlog drains; incident closed |

**Time to detect:** 49 minutes (09:14 → 10:03)
**Time to mitigate after detection:** 41 minutes (10:03 → 10:44)

Detection dominated the outage. Once someone was looking, diagnosis and rollback took a reasonable 41 minutes.

## Root cause

v4.7.0 changed the thumbnail generator to shell out to an `ImageMagick` binary. The production container image does not include that binary, so every thumbnail generation call failed, and every upload failed with it.

The change reached production without the missing dependency being caught because three independent safeguards each had a gap:

**The production image is built from a different Dockerfile than the one used in CI.** CI validated a container that is not the container that runs in production. A dependency added to the CI image — or present there incidentally — carries no guarantee about the production image. This is the direct cause: the two images had diverged, and nothing checked that they agreed.

**The integration test suite mocks the thumbnail generator.** The one test layer positioned to exercise the real binary substitutes a mock for it. The tests passed on a code path that does not exist in production.

**The alert measured HTTP status rather than application-level success.** The alert fired on 5xx rate. `media-service` returns 200 with an error body on upload failure, so a 100% failure rate registered as a 100% success rate. The alert was not broken; it was measuring the wrong thing, and would have stayed silent for any failure mode this service expresses in a response body.

Any one of these working would have caught the incident: a shared image would have failed the build, an unmocked integration test would have failed CI, and a success-rate alert would have paged within minutes instead of leaving detection to customers.

## What went well

- Once investigation began, root cause was identified in 17 minutes.
- Rollback was available, was the correct first move, and completed in 13 minutes.
- Failures were clean. Uploads were rejected rather than partially persisted, so recovery required no data repair and client retries succeeded unmodified.

## What went poorly

- Detection depended on customers noticing and complaining. Twenty-seven minutes passed before the first ticket and another 22 before anyone connected the tickets to an outage.
- A deploy took a core feature to 100% failure with no automated signal of any kind.
- The gap between the CI image and the production image meant CI could not have caught this class of defect, and this is unlikely to be the only dependency that differs between them.

## Action items

| # | Action | Type | Owner | Priority |
|---|---|---|---|---|
| 1 | Alert on application-level upload success rate, not HTTP status. Page when success rate drops below threshold over a short window | Detect | TBD | P0 |
| 2 | Audit `media-service` for other endpoints returning 200 on failure; either correct the status codes or ensure each has a success-rate alert | Detect | TBD | P1 |
| 3 | Build production images from the same Dockerfile CI validates. Until unified, add a CI check that fails when the two diverge | Prevent | TBD | P0 |
| 4 | Add an integration test that exercises the real thumbnail generator against the production image, unmocked | Prevent | TBD | P1 |
| 5 | Add a post-deploy smoke test that performs a real upload against production and rolls back automatically on failure | Mitigate | TBD | P1 |
| 6 | Establish a path for support ticket spikes to raise an engineering signal without waiting for someone to notice | Detect | TBD | P2 |

Items 1 and 3 are the highest-value pair: item 1 collapses the 49-minute detection gap to minutes, and item 3 closes the hole that let a missing dependency reach production at all.

## Open questions

- How many other dependencies differ between the CI and production images? Item 3 should be scoped from an inventory of the current divergence, not just a forward-looking check.
- Why does the upload endpoint return 200 on failure? If clients depend on that behavior, item 2 may require a coordinated client change.