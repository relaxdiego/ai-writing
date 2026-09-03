# Incident postmortem: image upload failure following media-service v4.7.0

**Date:** 2025-07-14, 09:12–11:48 UTC (2h36m)
**Impact:** Image uploads failed for all users for 92 minutes. Roughly 18,000 uploads failed. No data was lost; clients retried successfully once the service recovered.

## Summary

The v4.7.0 release of `media-service` changed the thumbnail generator to shell out to an `ImageMagick` binary. That binary is present in the image CI builds but absent from the image we ship to production, because the two are built from different Dockerfiles. Every upload therefore failed at the thumbnail step from the moment the deploy landed. The failure was invisible to monitoring: the service caught the error and returned HTTP 200 with an error body, and our upload alert was defined on 5xx rate, so nothing fired. We learned about the outage from customer support tickets 49 minutes in, and an engineer began investigating at 10:03. Once the cause was identified the fix was a rollback, which restored uploads within 13 minutes.

## Timeline (UTC)

- **09:12** — `media-service` v4.7.0 deploys to production.
- **09:14** — Upload error rate rises from 0.2% to 100%. No alert fires; the service returns 200 with an error body and the alert measures 5xx rate.
- **09:41** — First customer support ticket arrives.
- **10:03** — An engineer notices the volume of tickets and starts investigating.
- **10:20** — Root cause identified: v4.7.0 requires an `ImageMagick` binary that the production container image does not contain.
- **10:31** — Rollback to the prior version begins.
- **10:44** — Rollback complete. Uploads recover.
- **11:48** — Backlog of client-retried uploads drains. Incident closed.

## What went wrong

Three independent safeguards failed, and each of them failed for a reason that predates this release.

The production container image is built from a different Dockerfile than the one CI uses. A new runtime dependency added to the CI image is therefore not added to the production image, and nothing in the pipeline compares the two. Any change of this shape will pass every test and fail on deploy, so the divergence is a standing hazard rather than a detail of this incident.

The integration test suite mocks the thumbnail generator. Mocking it removes the only test path that would have executed the new binary, which means the suite cannot distinguish "the generator works" from "the generator is absent." The tests passed on a code path that does not exist in production.

The alert on upload health measured HTTP status rather than application-level success. The service degraded gracefully in the sense that it returned a well-formed 200 response describing the failure, and that graceful degradation is precisely what hid a total outage from monitoring for 49 minutes. Detection came from customers, and the 22 minutes between the first ticket and an engineer looking at it reflect that support ticket volume is not a signal routed anywhere an on-call engineer sees.

## What went well

Once someone was looking, diagnosis took 17 minutes and remediation took another 11. The rollback path worked as designed. Client-side retry behaviour meant that the 18,000 failed uploads were recovered by the clients themselves rather than requiring manual replay, which is why the incident cost no data.

## Action items

The container image divergence should be closed by building the production image from the same Dockerfile CI uses, or by promoting the exact artifact CI tested rather than rebuilding for production. Until one of those lands, a pipeline check that diffs the installed package sets of the two images would catch the same class of error.

At least one integration test must exercise the real thumbnail generator inside the production image. A single smoke test that uploads a fixture image and asserts a thumbnail comes back would have failed this release.

Upload alerting needs to move to an application-level success metric — the ratio of uploads that produce a stored thumbnail to uploads attempted — rather than HTTP status. This applies beyond uploads: any endpoint that returns 200 with an error body is currently unmonitored by the same reasoning, and that inventory is worth taking.

Finally, a deploy of `media-service` should be followed by an automatic post-deploy check against the same success metric, so that a release that breaks a core path is caught in minutes by the system that shipped it rather than in an hour by customers.