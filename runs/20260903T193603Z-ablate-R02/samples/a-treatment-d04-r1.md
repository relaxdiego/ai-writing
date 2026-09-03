# Postmortem: image upload failure after media-service v4.7.0

**Date:** 2025-07-14, 09:12–11:48 UTC (2h36m)
**Status:** Resolved by rollback
**Severity:** Full loss of a core feature for all users

## Summary

The v4.7.0 release of `media-service` changed the thumbnail generator to invoke an ImageMagick binary. That binary is not present in the production container image, so every upload failed at the thumbnail step from the moment the deploy landed. Roughly 18,000 uploads failed. No data was lost; failed uploads were rejected outright rather than partially written, and clients retried successfully once the service recovered.

Uploads were broken for 1h30m, from 09:14 to 10:44. The incident remained open for a further hour while the retry backlog drained.

No alert fired at any point. The failure was detected by customers, and reached an engineer 49 minutes after it began.

## Timeline (UTC)

- **09:12** — `media-service` v4.7.0 deployed to production.
- **09:14** — Upload error rate rises from 0.2% to 100%. No alert fires: the alert is defined on 5xx rate, and the failing path returns HTTP 200 with an error body.
- **09:41** — First customer support ticket.
- **10:03** — An engineer notices the volume of tickets and begins investigating.
- **10:20** — Cause identified: v4.7.0 requires an ImageMagick binary absent from the production container image.
- **10:31** — Rollback to the previous version started.
- **10:44** — Rollback complete. Uploads recover.
- **11:48** — Backlog of retried uploads drains. Incident closed.

## Root cause

The thumbnail generator in v4.7.0 shells out to ImageMagick. The production container image does not include that binary, so the call failed on every request. Because the upload handler reported this failure in the response body rather than in the status code, each failure was recorded as a successful HTTP transaction.

## Contributing factors

Three things had to be true at once for a missing binary to become a two-and-a-half-hour outage.

The production container image is built from a different Dockerfile than the one CI uses. A dependency can therefore be added, satisfied in CI, and still be absent in production, with nothing in the pipeline comparing the two. This is what let the change ship.

The integration suite mocks the thumbnail generator, so no test in the pipeline ever executed the new code path against a real binary. The mock made the test suite indifferent to the very change under test.

The upload alert measured HTTP status rather than application-level success. A handler that returns 200 with an error body is invisible to it. This is what turned a bad deploy into an outage found by customers: a complete, sustained failure of a core feature produced no signal at all in monitoring.

The first two factors are about how the defect shipped. The third is the more serious one, because it applies to every future failure of this shape, not just this one.

## What went well

Once an engineer was engaged, diagnosis took 17 minutes and rollback a further 13. The rollback path itself worked cleanly and uploads recovered immediately.

## Action items

Owners and target dates are not recorded in the source notes and need to be assigned before this document is filed.

1. **Build production images from the same Dockerfile as CI**, or, if they must diverge, add a pipeline check that fails when the runtime dependencies of the two images differ. This is the fix that would have prevented the incident.
2. **Alert on upload success rate measured at the application level**, not on HTTP status. Page when the rate falls below threshold for a short sustained window.
3. **Audit other alerts for the same defect.** Any endpoint that can return 200 on failure is currently unmonitored, and the upload path is unlikely to be the only one.
4. **Replace the thumbnail generator mock** in at least one integration test with a run against the real production image, so that missing runtime dependencies fail the build.
5. **Make the handler return a 5xx** when thumbnail generation fails. This does not replace item 2, but it restores the default behaviour that the existing alerting assumes.

## Open questions

The notes do not record why 22 minutes passed between the first support ticket at 09:41 and an engineer picking it up at 10:03, nor whether support has a path to escalate a spike in tickets directly to on-call. If no such path exists, that gap will recur on the next incident that monitoring misses.