# Incident postmortem: image upload failure, 2025-07-14

## Summary

Between 09:12 and 11:48 UTC on 14 July 2025, image uploads failed for every user of the service. A deploy of `media-service` v4.7.0 introduced a dependency on the `ImageMagick` binary, which is not present in the production container image, so every thumbnail generation attempt failed. Roughly 18,000 uploads were rejected over the two hours and thirty-six minutes the incident was open. No data was lost: uploads that failed returned an error to the client rather than being silently dropped, and the retry backlog drained cleanly once the service recovered.

## Timeline (UTC)

- **09:12** — v4.7.0 deploys to production.
- **09:14** — Upload error rate rises from 0.2% to 100%. No alert fires.
- **09:41** — First customer support ticket arrives.
- **10:03** — An engineer notices the growing ticket volume and begins investigating.
- **10:20** — The engineer identifies the missing `ImageMagick` binary as the cause.
- **10:31** — Rollback to v4.6.x begins.
- **10:44** — Rollback completes; uploads recover.
- **11:48** — Retry backlog drains and the incident is closed.

## What happened

Version 4.7.0 changed the thumbnail generator to shell out to `ImageMagick`. That binary exists in the image CI builds and tests against, but production containers are built from a separate Dockerfile that does not install it, so the call failed on every upload in production while passing everywhere else. The failure was handled inside the request path rather than propagating: the service caught the error, returned HTTP 200, and put the failure in the response body. Clients treated the upload as rejected and surfaced an error to users, but every layer of monitoring between the service and the on-call engineer saw a healthy 200.

Detection therefore fell entirely to customers. The first ticket arrived twenty-seven minutes after the breakage, and it took another twenty-two minutes for anyone to read enough tickets to recognise a systemic outage rather than a scattering of individual complaints. Once an engineer was actually looking, diagnosis and remediation were fast: seventeen minutes to identify the missing dependency, eleven more to start the rollback, and thirteen for it to complete. The user-visible outage ran ninety minutes, of which roughly fifty-one were spent before anyone knew there was an incident at all.

## Contributing factors

The proximate cause was a dependency added in code without being added to the production image, but three conditions had to hold at once for that mistake to reach users and stay there.

Production containers are built from a different Dockerfile than the one CI uses. This means the artefact that gets tested is not the artefact that gets deployed, and any divergence between the two files is invisible until runtime. A missing binary is the mildest version of this class of bug; a divergent library version would have been considerably harder to diagnose.

The integration test suite mocks the thumbnail generator. The one test layer positioned to catch a broken generator had been configured not to exercise it, so the suite passed on a build that could not generate a single thumbnail.

The upload alert measured 5xx rate rather than application-level upload success. Because the service reported failures with a 200 status and an error body, a total outage was indistinguishable from normal operation at the level the alert was watching.

## Action items

Consolidate the CI and production Dockerfiles into a single file, or, if they must differ, have CI build and test the exact image that will be deployed. Until the tested artefact and the shipped artefact are the same thing, this failure mode remains available.

Replace the mock in the integration suite with the real thumbnail generator running against the production image, so that a missing or broken dependency fails the build rather than the deploy.

Re-base the upload alert on application-level success rate, computed from the response body rather than the HTTP status, and add a synthetic upload probe that exercises the full path end to end. Either change alone would have cut roughly fifty minutes off detection time.

Separately, review other endpoints that return errors with a 200 status. The pattern is likely not unique to uploads, and every instance of it is a place where monitoring is blind to a total failure.