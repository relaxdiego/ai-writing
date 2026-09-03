# Image upload outage, 2025-07-14

## Summary

Between 09:12 and 11:48 UTC on 14 July 2025, image uploads failed for every user of the service. The failure was introduced by the deploy of `media-service` v4.7.0, which changed the thumbnail generator to shell out to an `ImageMagick` binary that is not present in the production container image. Roughly 18,000 uploads failed over the 2h36m of the incident. No data was lost: the failures occurred before any write was committed, and clients retried successfully once the service recovered.

Nothing alerted. The failing code path returned HTTP 200 with an error body, and the paging alert was defined on 5xx rate, so from the monitoring system's point of view the service was healthy for the full duration. The outage was discovered by an engineer who noticed support ticket volume 49 minutes after it began.

## Timeline

- **09:12** — `media-service` v4.7.0 deployed to production.
- **09:14** — Upload error rate rises from 0.2% to 100%. No alert fires.
- **09:41** — First customer support ticket.
- **10:03** — An engineer notices the ticket volume and begins investigating.
- **10:20** — Cause identified: v4.7.0 requires an `ImageMagick` binary absent from the production image.
- **10:31** — Rollback to v4.6.x begins.
- **10:44** — Rollback complete; uploads recover.
- **11:48** — Backlog of client-retried uploads drains. Incident closed.

Of the 2h36m, 89 minutes elapsed before anyone was investigating, 17 minutes were spent on diagnosis, 13 on the rollback itself, and the remaining 64 on draining the retry backlog.

## What went wrong

The immediate cause is a missing runtime dependency, but the more useful question is why three separate mechanisms that should have caught it did not.

The production container image is built from a different Dockerfile than the one CI uses. This means CI's image is not evidence about production's image, and a change that adds a system-level dependency can pass every check while producing a production artifact that cannot run the new code. The divergence has presumably existed for some time and has been harmless up to now because dependency changes have been confined to the application's own package manifest.

The integration test suite mocks the thumbnail generator. The one test layer positioned to exercise the real binary substitutes a stand-in for it, so the suite would have passed identically whether or not `ImageMagick` was installed anywhere.

The alert measured HTTP status rather than application-level success. The service's convention of returning 200 with an error body is not itself unusual, but it makes status code a meaningless health signal for this endpoint, and the alert was never updated to reflect that. Detection therefore fell to customers, at a cost of about 49 minutes before the first ticket arrived and another 22 before ticket volume was noticed.

## Remediation

The Dockerfile divergence is the root fix and should come first: CI and production must build from the same file, and if there is a reason the production build differs, the difference belongs in build arguments rather than a separate file. Until that lands, a smoke test that runs the production image and exercises one real upload end to end will catch this class of failure at deploy time.

The integration suite should exercise the real thumbnail generator against the real image. Mocking is defensible for unit tests; at the integration layer it removed the only check on the boundary that broke.

The upload alert should be redefined on application-level upload success rate rather than 5xx rate, with a threshold that would have fired within a minute or two of 09:14. Any other endpoint following the 200-with-error-body convention needs the same review, since the same blind spot applies to all of them.

Finally, the 22 minutes between the first ticket and an engineer looking at it suggests support ticket volume should feed a low-priority signal into the on-call channel. It is a weak detector and no substitute for the alert fix, but it was the only detector that worked here.