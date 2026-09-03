# Postmortem: Image Upload Failure (2025-07-14)

**Status:** Resolved
**Duration:** 2025-07-14 09:12–11:48 UTC (2h36m); user-visible failures 09:14–10:44 (1h30m)
**Impact:** Image uploads failed for 100% of users, approximately 18,000 failed upload attempts. No data loss occurred — failures happened before any write was committed, and clients retried successfully once the service recovered.

## Summary

The 09:12 deploy of `media-service` v4.7.0 shipped a thumbnail generator that shells out to an `ImageMagick` binary, which is not present in the production container image. Every upload began failing two minutes later, but the failure was invisible to our monitoring because the service returned HTTP 200 with an error payload rather than a 5xx, and our upload alert measured 5xx rate. The outage was discovered 49 minutes later by an engineer who noticed unusual support ticket volume, diagnosed by inspecting the release diff, and resolved by rolling back to v4.6.x. Uploads recovered at 10:44 and the retry backlog finished draining at 11:48.

## Timeline (UTC)

| Time | Event |
|---|---|
| 09:12 | `media-service` v4.7.0 deployed to production |
| 09:14 | Upload error rate rises from 0.2% to 100%; no alert fires |
| 09:41 | First customer support ticket filed |
| 10:03 | Engineer notices ticket volume and begins investigating |
| 10:20 | v4.7.0 identified as the cause: thumbnail generator requires an `ImageMagick` binary absent from the production image |
| 10:31 | Rollback initiated |
| 10:44 | Rollback complete; uploads recover |
| 11:48 | Backlog of retried uploads drains; incident closed |

## Root cause

The v4.7.0 change to the thumbnail generator introduced a dependency on the `ImageMagick` binary at runtime. That dependency was satisfied in every environment where the code was exercised before release but not in production, because the production container image is built from a different Dockerfile than the image CI builds and tests against. The two files have drifted, and nothing in the pipeline compares them or fails when a dependency exists in one and not the other, so a change can pass every gate we have and still land on a host that cannot run it.

The integration test suite would ordinarily be the place this surfaced, but it mocks the thumbnail generator, which means the tests exercised the code path that calls the generator without ever invoking the binary the generator now needed. The mock was introduced for speed and determinism and did its job for the logic under test; the cost is that the suite gives no signal at all about the generator's runtime environment, and we had been reading a green suite as broader assurance than it actually provided.

## Why detection took 49 minutes

When the generator failed, the upload handler caught the error and returned HTTP 200 with an error body describing the failure. Our upload alert thresholds on 5xx rate, so from the alert's perspective the service was returning successful responses at a normal rate throughout the outage. The monitoring was measuring transport-level status rather than whether the operation the user requested had actually completed, and the gap between those two things is exactly where this failure lived. Detection ultimately came from customers: the first ticket arrived at 09:41, 27 minutes into the outage, and it took another 22 minutes for the accumulating volume to draw an engineer's attention, since no one was watching for a ticket spike as a signal either.

Once someone was looking, resolution was quick. Seventeen minutes from the start of investigation to a confirmed diagnosis and another 24 minutes to a completed rollback is a reasonable showing, and it suggests our response tooling is sound while our detection is not.

## What went well

The rollback path worked exactly as designed and required no improvisation — the previous version was still available, the deploy tooling reverted cleanly, and recovery was immediate on completion. Client-side retry behavior meant that most affected uploads eventually succeeded without users having to re-initiate them, which is why an outage that failed 18,000 requests produced no data loss and a comparatively small volume of support contact.

## Action items

| # | Action | Owner | Priority |
|---|---|---|---|
| 1 | Build the container image once in CI and promote that exact artifact to production; delete the production-only Dockerfile | Platform | P0 |
| 2 | Add an application-level alert on upload success rate (successful completions / attempts), independent of HTTP status | Media | P0 |
| 3 | Return 5xx for server-side upload failures instead of 200 with an error body; audit other handlers for the same pattern | Media | P1 |
| 4 | Add a post-deploy smoke test that performs a real upload through the full generator path against the deployed image, and gate the deploy on it | Media | P1 |
| 5 | Replace or supplement the thumbnail generator mock with at least one integration test that invokes the real binary in the production image | Media | P1 |
| 6 | Route support ticket volume spikes to an on-call signal so customer reports reach engineers faster than 22 minutes | Support / SRE | P2 |

Items 1 and 2 address the two failures that made this incident possible at all — an untested production artifact and a health signal that could not see the failure. The remainder shorten the detection and diagnosis window if something similar slips through again.