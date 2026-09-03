# Incident postmortem: image upload failure following media-service v4.7.0

## Summary

On 14 July 2025, image uploads failed for all users for 2 hours and 36 minutes, from 09:12 to 11:48 UTC. Approximately 18,000 upload attempts failed during the window. No data was lost: every failed upload was rejected at ingest rather than partially written, and the client retry path drained cleanly once service was restored. The cause was a deploy of `media-service` v4.7.0, which introduced a dependency on an `ImageMagick` binary that was not present in the production container image. The failure was total from the moment of deploy, but no alert fired, because the service returned HTTP 200 with an error body and our alerting measured 5xx rate. Detection came from customer support ticket volume, 49 minutes after the failure began, and an engineer began investigating 51 minutes after that.

## Timeline (UTC)

- 09:12 — `media-service` v4.7.0 deployed to production.
- 09:14 — Upload error rate rises from 0.2% to 100%. No alert fires.
- 09:41 — First customer support ticket received.
- 10:03 — An engineer notices the ticket volume and begins investigating.
- 10:20 — Root cause identified: v4.7.0 changed the thumbnail generator to invoke an `ImageMagick` binary absent from the production container image.
- 10:31 — Rollback to v4.6.x started.
- 10:44 — Rollback complete; uploads recover.
- 11:48 — Backlog of retried uploads drains; incident closed.

## What happened

Version 4.7.0 reworked the thumbnail generator to shell out to `ImageMagick`. In CI the change passed, and it passed for two reasons that reinforced each other. The integration suite mocks the thumbnail generator, so no test in the pipeline ever executed the new code path against a real binary; and the container image used in CI is built from a different Dockerfile than the one that produces the production image, so even a test that had exercised the path would have run in an environment where the binary happened to be available. The production image had no `ImageMagick`, the generator's invocation failed on every upload, and the service caught that failure and returned a 200 response carrying an error payload.

That response shape is what made a total outage invisible to monitoring. The upload alert was defined on HTTP 5xx rate, which stayed flat at zero throughout, so a 100% application-level failure rate produced no signal at all. The 49 minutes between the failure and the first support ticket, and the 22 minutes after that before anyone looked at the tickets, are both consequences of having no automated detection: the only monitor we had was our customers.

## Contributing factors

Three things had to be true for this incident to happen as it did. The CI container image and the production container image are built from separate Dockerfiles, so the environment we test in is not the environment we ship, and a missing runtime dependency is undetectable before deploy. The integration test suite mocks the thumbnail generator rather than running it, which removes the last opportunity to catch a broken invocation. And the alert on the upload path measured transport status rather than application outcome, so a service that reliably answered every request with a failure looked healthy.

## Remedial actions

The production Dockerfile should become the single image definition, with CI building and testing the artifact that is actually deployed. Until that consolidation lands, a startup check in `media-service` that verifies the presence and version of every external binary it invokes will turn a silent runtime failure into a crash loop that blocks the rollout.

At least one integration test must exercise the thumbnail generator unmocked against the real image, so that the class of bug we shipped here cannot pass the pipeline again. Mocking is appropriate for the upstream callers of the generator, but there needs to be a seam somewhere in the suite where the real dependency runs.

Alerting on the upload path needs to move to an application-level success metric, counting successful uploads rather than non-5xx responses, with a page firing on a sustained drop below threshold. The general form of that rule should be applied wherever a service returns a 200 with an error body: our alerts currently assume that status code and outcome agree, and this incident shows what that assumption costs. A deploy-correlated check, comparing the success metric before and after each release and halting the rollout on a sharp regression, would have caught this within the two minutes it took the error rate to reach 100%.