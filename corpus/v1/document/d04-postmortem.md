---
id: d04
register: document
name: Incident postmortem
---
Write an incident postmortem from these notes.

Duration: 2025-07-14 09:12 UTC to 11:48 UTC (2h36m).
Impact: image uploads failed for all users; roughly 18,000 failed uploads; no data loss.

Timeline notes:
- 09:12 deploy of `media-service` v4.7.0 goes out
- 09:14 upload error rate goes from 0.2% to 100%; no alert fires because the alert was on 5xx rate and the service returned 200 with an error body
- 09:41 first customer support ticket
- 10:03 engineer notices the ticket volume, starts investigating
- 10:20 identifies v4.7.0 changed the thumbnail generator to require an `ImageMagick` binary that is not in the production container image
- 10:31 rollback started
- 10:44 rollback complete, uploads recover
- 11:48 backlog of retried uploads drains, incident closed

Contributing factors: the container image is built from a different Dockerfile than the one used in CI; the integration test suite mocks the thumbnail generator; the alert measured HTTP status rather than application-level success.
