# Incident postmortem: image upload failures, 2025-07-14

## Summary

Between 09:12 and 11:48 UTC on 14 July 2025, image uploads failed for every user of the platform. The failure began two minutes after the deploy of `media-service` v4.7.0, which introduced a dependency on an `ImageMagick` binary that was absent from the production container image. Roughly 18,000 uploads failed over the 2 hours and 36 minutes the incident was open. No data was lost: uploads either failed outright or were retried successfully once the service recovered, and the retry backlog drained by 11:48.

The most costly part of this incident was not the bug but the 51 minutes between the failure starting and anyone knowing about it. The service returned HTTP 200 with an error body, so the alert on 5xx rate stayed silent, and the first signal we received was a customer support ticket at 09:41.

## Timeline (UTC)

- **09:12** — `media-service` v4.7.0 deployed to production.
- **09:14** — Upload error rate rises from a baseline of 0.2% to 100%. No alert fires; the failing responses carry a 200 status with an error body, and the alert is defined on 5xx rate.
- **09:41** — First customer support ticket arrives.
- **10:03** — An engineer notices the rising ticket volume and begins investigating.
- **10:20** — Cause identified: v4.7.0 changed the thumbnail generator to shell out to `ImageMagick`, which is not installed in the production container image.
- **10:31** — Rollback to the previous version begins.
- **10:44** — Rollback complete; uploads recover immediately.
- **11:48** — Backlog of retried uploads finishes draining. Incident closed.

## What happened

Version 4.7.0 of `media-service` reworked thumbnail generation to invoke the `ImageMagick` binary as a subprocess. That binary is present in the image CI builds and runs tests against, but not in the image we ship to production, because the two images are built from different Dockerfiles that have drifted apart. Every upload reaching the thumbnail step therefore failed at the point of invoking a binary that did not exist, and since the upload handler treated thumbnail failure as a recoverable application-level error rather than a server error, it returned a 200 response carrying an error payload. Clients read that payload correctly and reported the upload as failed to users, but every layer of our monitoring between the client and the service saw a successful request.

## Contributing factors

Three independent gaps had to line up for a missing binary to become a two-and-a-half-hour outage, and each of them is worth treating separately.

The production container image is built from a different Dockerfile than the one used in CI. This means CI cannot, in principle, tell us whether a new runtime dependency will be present in production; the two images are related only by convention and by whoever remembers to update both.

The integration test suite mocks the thumbnail generator. Even had the Dockerfiles been unified, the tests exercising the upload path never invoke the real generator, so the missing binary would not have surfaced. The mock was introduced to keep the suite fast, which is a reasonable goal, but it removed the last place where a dependency error could have been caught before deploy.

The alert measured HTTP status rather than application-level success. Our alerting assumed that a failing request produces a failing status code, and the upload handler's error semantics violated that assumption without anyone noticing the mismatch. This is the factor that converted a bad deploy, which should have been a five-minute rollback, into an outage measured in hours.

## Action items

1. **Unify the CI and production container images.** Build one image from one Dockerfile and promote the artefact CI tested through to production, rather than rebuilding at deploy time. (Owner: Platform)
2. **Run at least one integration test against the real thumbnail generator.** The suite can keep its mocks for breadth, but the primary upload path needs an unmocked test that would fail if the binary or its dependencies were missing. (Owner: Media)
3. **Alert on application-level upload success rate, not HTTP status.** Add an alert on the ratio of successful uploads to attempted uploads, with a page threshold well below the 100% failure we saw here. (Owner: Media / Observability)
4. **Audit other handlers that return 200 on failure.** Where an error is genuinely recoverable the status may be defensible, but each case needs a corresponding application-level metric, and we should know how many such cases exist. (Owner: Media)
5. **Review the escalation path from support tickets.** Twenty-two minutes passed between the first ticket and an engineer engaging with it; a volume-based trigger from the support queue into on-call would have shortened this. (Owner: Support / On-call)