# Incident postmortem: image upload failure following media-service v4.7.0

**Date:** 2025-07-14, 09:12–11:48 UTC (2h 36m)
**Impact:** All image uploads failed for all users for the duration of the incident, an estimated 18,000 failed upload attempts. No data was lost; failed uploads were retried successfully once the service recovered.

## Summary

The 09:12 deploy of `media-service` v4.7.0 introduced a dependency on the `ImageMagick` binary in the thumbnail generation path. That binary is not present in the production container image, so every upload failed at thumbnail generation from 09:14 onward. The failure was invisible to monitoring because the service returned HTTP 200 with an error body, and our upload alert measured 5xx rate. Detection came from customer support ticket volume roughly 50 minutes into the outage, and the incident was mitigated by rolling back to the prior version.

## Timeline (UTC)

- **09:12** — `media-service` v4.7.0 deployed to production.
- **09:14** — Upload error rate rises from 0.2% to 100%. No alert fires: the alert threshold is on 5xx rate, and the failing responses carry a 200 status with an error body.
- **09:41** — First customer support ticket filed.
- **10:03** — An engineer notices the accumulating ticket volume and begins investigating.
- **10:20** — Root cause identified: v4.7.0 changed the thumbnail generator to shell out to `ImageMagick`, which is absent from the production container image.
- **10:31** — Rollback to the previous version begins.
- **10:44** — Rollback complete; uploads recover.
- **11:48** — Backlog of client-retried uploads drains and the incident is closed.

## What went wrong

Three independent gaps had to line up for a missing binary to become a two-and-a-half-hour total outage, and each of them is worth treating separately.

The first is that production containers are built from a different Dockerfile than the one CI uses. Any change that adds a system-level dependency can therefore pass every build and test stage and still arrive in production without the dependency installed. The code change itself was correct; the environment it landed in was not the environment it had been validated against, and nothing in the pipeline compares the two.

The second is that the integration test suite mocks the thumbnail generator. The one test layer positioned to exercise the real code path, and thus to notice that a binary was missing, had that path stubbed out. The suite passed because it was not testing the thing that broke.

The third gap is the one that turned a bad deploy into a long outage. Our upload health alert measures HTTP status codes, but the service signals application errors in the response body while returning 200. From the monitoring system's point of view nothing changed at 09:14: traffic was steady and every response was successful. We had no automated detection at all, and the effective alerting mechanism was customers writing in. That accounts for the 49 minutes to the first ticket and a further 22 before anyone connected the tickets to an outage.

Once someone was actually looking, response was fast: 17 minutes to root cause and 11 more to begin rollback. The problem is entirely in the 51 minutes before that.

## Action items

**Unify the container build.** Production images must be built from the same Dockerfile CI uses, or the pipeline must fail when the two diverge. This removes the class of failure rather than this one instance of it.

**Alert on application-level upload success, not HTTP status.** The upload alert should fire on the rate of successful upload completions as the application defines success. As a follow-up, `media-service` should return non-2xx status codes for failed uploads, so that status-based tooling elsewhere is not similarly misled.

**Exercise the real thumbnail path in integration tests.** At minimum, one test should run thumbnail generation unmocked against the production image, which would have caught the missing binary before deploy.

**Add a smoke test to the deploy pipeline.** A single real upload against the newly deployed version, gating promotion, would have caught this at 09:13 rather than 10:03.

**Review other alerts for the same status-versus-outcome mismatch.** The upload alert is unlikely to be the only one measuring transport-level health as a proxy for whether the feature works.