# Incident Postmortem: Image Upload Failure (2025-07-14)

## Summary

Between 09:12 and 11:48 UTC on 2025-07-14, image uploads failed for all users of the platform, a window of 2 hours and 36 minutes during which roughly 18,000 upload attempts were rejected. The cause was a deploy of `media-service` v4.7.0 whose thumbnail generator invoked an `ImageMagick` binary that was absent from the production container image, so every upload failed at the thumbnailing step. No data was lost: uploads either failed before persistence or were retried successfully after recovery, and the retry backlog drained cleanly by 11:48.

The failure itself was total and immediate, but the response was slow — 51 minutes passed before anyone knew there was a problem, and that delay came entirely from monitoring that could not see the failure. The service returned HTTP 200 with an error payload, and the alert watched 5xx rates, so a 100% failure rate looked identical to perfect health.

## Timeline (UTC)

| Time | Event |
|---|---|
| 09:12 | `media-service` v4.7.0 deployed to production |
| 09:14 | Upload error rate rises from 0.2% to 100%; no alert fires |
| 09:41 | First customer support ticket filed |
| 10:03 | Engineer notices ticket volume and begins investigating |
| 10:20 | Root cause identified: v4.7.0 requires an `ImageMagick` binary missing from the production image |
| 10:31 | Rollback initiated |
| 10:44 | Rollback complete; uploads recover |
| 11:48 | Retried-upload backlog drains; incident closed |

## Root Cause

Version 4.7.0 changed the thumbnail generator to shell out to `ImageMagick` rather than use the previous in-process library. The dependency was added to the CI Dockerfile but not to the separate Dockerfile used to build production images, so the binary was present everywhere the change was tested and absent in the only environment that mattered. Because the thumbnail step ran inside the upload request path and its failure was caught and returned as a 200-with-error-body, the outage presented to monitoring as normal traffic.

## Contributing Factors

Three independent gaps had to line up for this to reach production undetected, and each is worth treating separately.

The production container image is built from a different Dockerfile than the one CI uses. Any dependency added to one and not the other produces a service that passes every test and fails on deploy, with no signal in between; this incident is the general case of that divergence, not a special case.

The integration test suite mocks the thumbnail generator. Mocking removed the one test that would have exercised the real binary, which meant the suite could not have caught a missing-binary failure regardless of which Dockerfile it ran against.

The upload alert measured HTTP status rather than application-level success. The service's own convention of returning 200 with an error body — not itself unreasonable for a partial-success API — made status code a meaningless health proxy, and the alert inherited that meaninglessness without anyone noticing.

## What Went Well

Once investigation started, diagnosis was fast: 17 minutes from first look to identified root cause, and 11 more to rollback. The rollback itself was clean and uploads recovered immediately. Client-side retry behaviour meant the user-visible impact was largely deferred rather than permanent, and no data was lost.

## Action Items

| # | Action | Owner | Priority |
|---|---|---|---|
| 1 | Alert on application-level upload success rate, not HTTP status; page on sustained failure above 5% | Platform | P0 |
| 2 | Consolidate CI and production builds onto a single Dockerfile | Media | P0 |
| 3 | Add a post-deploy smoke test that performs a real upload with real thumbnailing against production | Media | P1 |
| 4 | Add an integration test that exercises the unmocked thumbnail generator in the production image | Media | P1 |
| 5 | Audit remaining alerts for status-code-based health checks on endpoints that return 200 on error | Platform | P2 |

Items 1 and 2 are the ones that matter most: the first would have cut 49 minutes off detection, and the second would have prevented the deploy entirely.