# Postmortem: image upload failures after media-service v4.7.0

## Summary

On 2025-07-14, between 09:12 and 11:48 UTC, image uploads failed for every user of the service. The failure began two minutes after the deploy of `media-service` v4.7.0, which changed the thumbnail generator to invoke an `ImageMagick` binary that is not present in the production container image. Roughly 18,000 uploads failed over the 2h36m window. No data was lost; clients retried, and the retry backlog drained by 11:48.

The outage was total from the first affected request, but no alert fired. The upload path caught the thumbnail failure and returned HTTP 200 with an error body, and the alert that would have caught this measured 5xx rate rather than application-level upload success. Detection therefore came from customer support: the first ticket arrived 27 minutes into the outage, and an engineer noticed the ticket volume 49 minutes in. Once someone was looking, the rest moved quickly, with 17 minutes to root cause and 24 more to a completed rollback.

## Impact

All image uploads failed between 09:14 and 10:44, a 90-minute window of complete unavailability for that path. Approximately 18,000 upload attempts failed. Because failures were returned as 200 responses, any client that checks only the HTTP status may have reported success to its user while discarding the image; we have confirmed no data loss on our side, but the client-visible behaviour during the window was inconsistent rather than uniformly a visible error. Other service functions were unaffected.

## Timeline (UTC)

- 09:12 — `media-service` v4.7.0 deployed to production.
- 09:14 — Upload error rate rises from 0.2% to 100%. No alert fires; the service returns 200 with an error body, and the alert is bound to 5xx rate.
- 09:41 — First customer support ticket.
- 10:03 — An engineer notices the ticket volume and begins investigating.
- 10:20 — Root cause identified: v4.7.0's thumbnail generator requires an `ImageMagick` binary absent from the production container image.
- 10:31 — Rollback to the previous version started.
- 10:44 — Rollback complete; uploads recover.
- 11:48 — Retry backlog drains; incident closed.

## Root cause

v4.7.0 replaced the in-process thumbnail generation path with one that shells out to `ImageMagick`. The production container image does not contain that binary, so every thumbnail generation attempt failed at process spawn, and the upload handler treated the failure as a per-request error rather than a startup or health-check failure. The service stayed up and healthy by every signal we monitor while serving nothing but failures.

Two independent gaps let the change reach production. The production container image is built from a different Dockerfile than the one CI uses, so the CI environment had `ImageMagick` available and the production environment did not; the dependency was satisfied in the only place it was ever exercised. Separately, the integration test suite mocks the thumbnail generator, so no test in any environment invoked the real binary. The change was, from the perspective of every automated check, correct.

## Why detection took 49 minutes

The alert on the upload path measured HTTP status codes. The handler's error behaviour was to return 200 with an error body, a convention that predates this incident and is used elsewhere in the service, so a 100% failure rate produced a completely clean 5xx graph. Nothing in our monitoring distinguished an upload that stored an image from one that returned an error object with the same status code. The first signal available to us was human: support ticket volume, noticed by an engineer who was not on call for this service and happened to be reading the queue.

## What went well

Once investigation started, diagnosis took 17 minutes and correlated the failure to the deploy quickly. The rollback was clean and completed in 13 minutes with no manual data repair required. Client retry behaviour absorbed the backlog without intervention, which is why 18,000 failed uploads produced zero lost images.

## Action items

Owners and target dates are not recorded in the incident notes and need to be assigned before this document is closed out.

1. **Alert on application-level upload success**, not HTTP status. The immediate fix is a success-rate metric emitted by the upload handler itself, alerting on a drop below threshold over a short window.
2. **Build the production image from the CI Dockerfile**, or build both from a shared base so that a dependency present in one is present in the other. The divergence, not the missing binary, is the reusable failure.
3. **Exercise the real thumbnail generator in at least one integration test** running against the production image. A mock is appropriate for testing upload logic; it cannot substitute for testing that the binary exists.
4. **Audit other handlers that return 200 with an error body** and either change them to return a status reflecting the outcome or ensure each has an application-level success metric behind it. This convention hid a total outage once and will do so again wherever it appears.
5. **Confirm client behaviour on 200-with-error-body responses** for the affected window, to establish whether any user was shown a success for an upload that did not store.