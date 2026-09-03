# Incident postmortem: image upload failure, 2025-07-14

Image uploads failed for all users for two hours and thirty-six minutes, from 09:12 to 11:48 UTC, with roughly 18,000 uploads failing during the window. No data was lost; every failed upload returned an error to the client rather than being silently accepted, and the retry backlog drained cleanly once service was restored.

The cause was a missing dependency in the production container image. Version 4.7.0 of `media-service` changed the thumbnail generator to shell out to an `ImageMagick` binary, and that binary is not present in the image we run in production. Every upload that reached thumbnail generation failed. The error rate went from 0.2% to 100% within two minutes of the deploy, but no alert fired, because our upload alert is defined on the HTTP 5xx rate and the service returned 200 with an error body. We therefore learned about the outage from customers: the first support ticket arrived at 09:41, twenty-seven minutes into the failure, and an engineer noticed the ticket volume and began investigating at 10:03. Diagnosis was fast once someone was looking, taking seventeen minutes from the start of the investigation, and rollback was underway by 10:31 and complete by 10:44. Uploads recovered immediately on rollback; the remaining hour was the retried-upload backlog draining, which it did without intervention, and we closed the incident at 11:48.

## Timeline (UTC)

- 09:12 — `media-service` v4.7.0 deployed to production
- 09:14 — upload error rate reaches 100%; no alert fires
- 09:41 — first customer support ticket
- 10:03 — engineer notices ticket volume, begins investigating
- 10:20 — missing `ImageMagick` binary in the production image identified as the cause
- 10:31 — rollback to v4.6.x started
- 10:44 — rollback complete, uploads recover
- 11:48 — retried-upload backlog drains, incident closed

## Contributing factors

Three failures lined up here, and each one independently would have kept the incident much smaller. The first is that the production container image is built from a different Dockerfile than the one CI uses. This means CI cannot tell us whether the artifact we ship will run, only whether some related artifact will, and a dependency added to one file and not the other produces a green build and a broken deploy. The divergence is the root cause: it is what allowed a change requiring a new system binary to reach production at all.

The second is that the integration test suite mocks the thumbnail generator. A test that exercised the real generator against the real image would have caught the missing binary regardless of the Dockerfile split, so this is the layer of defence that should have caught what the first one let through.

The third is the alert definition, which measured HTTP status rather than application-level success. A total upload failure was invisible to monitoring because the service was scrupulously returning 200. This did not cause the outage but it set its duration: with a correct alert we would have been paged at roughly 09:16 rather than reading about it in a support queue at 10:03, and the incident would likely have run under thirty minutes instead of two and a half hours.

## Action items

Owners and target dates still need to be assigned; the notes from the incident do not record them.

1. Build the production image from the same Dockerfile CI uses, or delete one of the two. This is the highest-value item and the only one that addresses the root cause.
2. Add an integration test that runs the real thumbnail generator inside the production image, so that missing system dependencies fail the build.
3. Redefine the upload alert on application-level success rate rather than HTTP status, and audit the remaining alerts for the same pattern. Any endpoint that can return 200 with an error body has this bug in its monitoring.
4. Review whether returning 200 with an error body is intended behaviour for the upload endpoint. If it is not, fixing it also repairs the alerting; if it is, the alerting fix above has to stand on its own.