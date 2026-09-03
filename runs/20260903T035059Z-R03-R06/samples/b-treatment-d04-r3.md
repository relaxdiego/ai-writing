# Incident postmortem: total image upload failure, 2025-07-14

## Summary

Between 09:12 and 11:48 UTC on 14 July 2025, image uploads failed for every user of the service, a window of two hours and thirty-six minutes during which roughly 18,000 upload attempts were rejected. The cause was a deploy of `media-service` v4.7.0 whose new thumbnail generator invoked an `ImageMagick` binary that is not present in the production container image. No data was lost: uploads failed before any partial write, and clients retried successfully once the rollback landed.

The failure itself was total and immediate, but the service continued to answer with HTTP 200 and an error body, so the alert watching 5xx rates saw a healthy system. Detection therefore fell to customers, and the first support ticket did not arrive until 09:41, with an engineer picking up the pattern at 10:03. Of the 92 minutes between breakage and diagnosis, 49 were spent with the system broken and nobody aware of it.

## Timeline (UTC)

- 09:12 — `media-service` v4.7.0 deploys to production.
- 09:14 — Upload error rate rises from 0.2% to 100%. No alert fires; the service returns 200 with an error body and the alert is bound to 5xx rate.
- 09:41 — First customer support ticket.
- 10:03 — An engineer notices the ticket volume and begins investigating.
- 10:20 — Root cause identified: v4.7.0's thumbnail generator requires an `ImageMagick` binary absent from the production container image.
- 10:31 — Rollback to the previous version begins.
- 10:44 — Rollback complete; uploads recover.
- 11:48 — Backlog of retried uploads drains; incident closed.

## What went wrong

Three independent safeguards would each have caught this, and each failed for its own reason. The production container image is built from a different Dockerfile than the one CI uses, so a dependency added to the CI image satisfies the build and the test run while leaving production without it; the two files drift by construction, and nothing compares them. The integration suite mocks the thumbnail generator, so the code path that shells out to the missing binary is never exercised against a real image in any environment before production. The upload alert measures HTTP status rather than application-level success, and because the handler catches generator failures and reports them in a 200 response body, the metric the alert watches was correct throughout the outage and the service it described was entirely down.

The rollback itself went well. Eleven minutes from diagnosis to rollback start and thirteen more to recovery is a reasonable response once the problem was understood, and the remaining 64 minutes to incident close were spent draining a retry backlog rather than fixing anything. The cost of this incident sits almost entirely in the time before 10:20.

## Actions

Alerting should move to an application-level success metric for uploads, so that a 200 carrying an error body counts as a failure. This is the single change that would have shortened the incident most, cutting roughly 49 minutes of blind time.

The production and CI Dockerfiles should be unified, or failing that, a build-time check should assert that every binary the service invokes at runtime is present in the production image. Until they are the same file, any dependency added in one place can go missing in the other.

At least one integration test should exercise the thumbnail generator against a real image in the production container, not a mock. The mock is defensible for speed in the broader suite, but a code path that shells out to an external binary needs one test that actually runs the binary in the environment where it is expected to exist.