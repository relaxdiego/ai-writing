# Incident postmortem: image upload failure, 2025-07-14

## Summary

Image uploads failed for all users for approximately 90 minutes following the deploy of `media-service` v4.7.0. The release changed the thumbnail generator to invoke an `ImageMagick` binary that is not present in the production container image, so every upload that reached thumbnail generation failed. Because the failure path returned HTTP 200 with an error body rather than a 5xx, no alert fired, and the outage was discovered only when an engineer noticed the support ticket volume 49 minutes after it began. Recovery was by rollback. There was no data loss.

## Impact

Roughly 18,000 uploads failed between 09:14 and 10:44 UTC, affecting all users of the upload path. Clients retried, and the resulting backlog took a further 64 minutes to drain; the incident was declared closed at 11:48 once the queue was clear. No uploads were lost, and no stored media was corrupted or deleted. The declared incident window of 09:12 to 11:48 (2h36m) is longer than the user-visible failure window of 09:14 to 10:44 (1h30m) because it spans the deploy that caused it and the backlog drain that followed it.

## Timeline

All times UTC.

| Time | Event |
| --- | --- |
| 09:12 | `media-service` v4.7.0 deployed to production |
| 09:14 | Upload error rate rises from 0.2% to 100%. No alert fires: the alert is defined on 5xx rate, and the service returns 200 with an error body |
| 09:41 | First customer support ticket |
| 10:03 | Engineer notices ticket volume and begins investigating |
| 10:20 | Cause identified: v4.7.0 requires an `ImageMagick` binary absent from the production container image |
| 10:31 | Rollback started |
| 10:44 | Rollback complete; uploads recover |
| 11:48 | Backlog of retried uploads drains; incident closed |

## Root cause

Version 4.7.0 changed the thumbnail generator to shell out to `ImageMagick`. The production container image does not contain that binary, so the call failed for every upload, and the generator's error handling translated the failure into an HTTP 200 response carrying an error body. To the load balancer, the metrics pipeline, and the alerting rules, the service therefore looked healthy for the entire outage.

Two independent defects had to line up for this to reach production undetected. The dependency was missing because the production container image is built from a different Dockerfile than the one CI uses, so a green CI run says nothing about what is installed in the image that actually ships. The missing dependency was not caught by tests because the integration suite mocks the thumbnail generator, leaving no test anywhere in the pipeline that exercises the real binary.

## Detection

Detection took 49 minutes from onset, against a diagnosis time of 17 minutes once someone was looking and a further 24 minutes to complete the rollback. The alert on 5xx rate could not fire, because the failing requests were not 5xx. The first external signal was a support ticket at 09:41, 27 minutes into the outage, and a further 22 minutes passed before an engineer noticed the accumulating ticket volume. The notes do not record what happened during those 22 minutes or whether support volume is routed to on-call in any structured way; that gap should be established before the corresponding action item below is scoped.

Returning 200 on an internal failure is a defect in its own right, separate from the choice of alert. It defeats client-side error handling, retry logic keyed on status, and any future monitoring that reads status codes, so fixing the alert without fixing the response code would leave most of the blast radius in place.

## What worked

Once investigation began, the release was correctly identified as the cause within 17 minutes and rollback was chosen immediately rather than a forward fix. The rollback itself completed in 13 minutes and restored service cleanly. Client retry behaviour preserved every upload that failed, which is why an outage of this length produced no data loss.

## Action items

Owners and due dates are not recorded in the source notes and need to be assigned before this document is circulated.

1. Build the production container image from the same Dockerfile CI tests against, or make CI build and test the production image directly. Until this holds, no CI result is evidence about production.
2. Fix the thumbnail generator to return a 5xx on internal failure rather than 200 with an error body.
3. Add an alert on application-level upload success rate, independent of HTTP status, with a threshold that would have fired within two minutes of 09:14.
4. Add at least one integration test that exercises the real thumbnail generator against the shipping image, with no mock in the path.
5. Add a startup check to `media-service` that verifies required external binaries are present and fails the deploy if they are not.
6. Establish a route from support ticket volume to on-call paging, so that a spike in tickets is a detection signal rather than something an engineer happens to see.