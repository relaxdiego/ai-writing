# Postmortem: media-service v4.7.0 image upload outage

**Date:** 2025-07-14, 09:12–11:48 UTC (2h36m)
**Status:** Resolved by rollback

## Summary

A release of `media-service` introduced a dependency on the `ImageMagick` binary, which is not present in the production container image, and every image upload failed for the two and a half hours until the release was rolled back. Roughly 18,000 uploads failed. No data was lost: clients retried, and the retry backlog drained by 11:48.

The failure was total and immediate, but nothing in our monitoring saw it. The upload path returned HTTP 200 with an error body, so the 5xx-rate alert never fired. The outage was discovered 49 minutes in, by a human noticing that support tickets were piling up.

## Impact

All users were unable to upload images for 2h36m. Approximately 18,000 upload attempts failed. Uploads recovered at 10:44 when the rollback completed; the remaining hour was the retried backlog draining, during which uploads succeeded but with elevated latency. No data was lost and no other service was affected.

## Timeline (UTC)

| Time | Event |
| --- | --- |
| 09:12 | `media-service` v4.7.0 deployed to production |
| 09:14 | Upload error rate rises from 0.2% to 100%. No alert fires: the service returns 200 with an error body, and the alert measures 5xx rate |
| 09:41 | First customer support ticket |
| 10:03 | Engineer notices ticket volume and begins investigating |
| 10:20 | Cause identified: v4.7.0's thumbnail generator requires an `ImageMagick` binary absent from the production container image |
| 10:31 | Rollback started |
| 10:44 | Rollback complete; uploads recover |
| 11:48 | Retry backlog drained; incident closed |

Two intervals are worth separating. Detection took 49 minutes and depended entirely on customers reporting the problem and an engineer happening to notice. Response, once someone was looking, was fast: 17 minutes to identify the cause and 24 minutes from identification to recovered service.

## Analysis

The proximate cause is a build-environment mismatch. v4.7.0 changed the thumbnail generator to shell out to `ImageMagick`, and that binary exists in the environment the change was developed and tested in but not in the image that runs in production. Every upload reached the thumbnail step and failed there.

Three separate defences should have caught this, and each failed for its own reason.

- **The production image is built from a different Dockerfile than the one CI uses.** This means CI never tests the artifact that ships. A missing runtime dependency is exactly the class of defect this divergence hides, and it will hide the next one too.
- **The integration test suite mocks the thumbnail generator.** With the generator mocked, the suite passes whether or not the real binary exists, so the tests confirmed that our code called the generator correctly and told us nothing about whether the generator could run.
- **The alert measured HTTP status rather than application-level success.** The service was healthy by every signal we watched: it was up, responding, and returning 200. Measuring transport-layer status as a proxy for whether the feature works means any failure mode that returns a well-formed response is invisible.

The first two factors let the defect reach production. The third is why it stayed there for 49 minutes without anyone knowing, and it is the most serious of the three, because it applies to failures well beyond this one.

## What went well

Once investigation started, diagnosis and rollback were quick and correct. The engineer went from ticket volume to identified root cause in 17 minutes, and chose rollback over a forward fix, which restored service in 13 minutes rather than the hour or more a container rebuild would have taken. Client-side retry behaviour meant the failed uploads were recoverable and no user data was lost.

## Action items

Owners and target dates are not assigned in the source notes and need to be set before this is closed out.

1. Alert on application-level upload success rate rather than HTTP status code, and audit the remaining alerts for the same substitution. This is the highest priority item: it converts a 49-minute customer-reported detection into a page within a minute or two.
2. Build the production container image from the same Dockerfile CI tests against, or, if the two must differ, run the CI suite against the production image before promotion.
3. Add at least one integration test that exercises the real thumbnail generator, unmocked, inside the production image. The mock is reasonable for the fast suite; there needs to be a slower path that does not use it.
4. Add a post-deploy smoke test that performs a real upload end to end and blocks or reverses the rollout on failure. This would have caught the outage at 09:13 regardless of the alerting and testing gaps above.