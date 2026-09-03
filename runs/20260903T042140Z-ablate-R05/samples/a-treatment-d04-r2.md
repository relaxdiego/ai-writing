# Image upload outage, 14 July 2025

Between 09:12 and 11:48 UTC, image uploads failed for every user of the platform. The immediate cause was a deploy of `media-service` v4.7.0, whose new thumbnail generator invoked an `ImageMagick` binary that is not present in the production container image; every upload that reached the thumbnailing step failed. Roughly 18,000 uploads failed over the 2h36m window. No data was lost: uploads either failed outright or were retried successfully once the rollback completed, and no stored media was corrupted or deleted.

The failure was total from 09:14, but no alert fired. The upload path returned HTTP 200 with an error in the response body, and our alerting measured 5xx rate, so the monitoring system saw a service returning successes at its usual volume. We learned about the outage from customers: the first support ticket arrived at 09:41, and an engineer noticed the accumulating ticket volume at 10:03, 49 minutes after the service broke.

## Timeline (all times UTC)

- 09:12 Deploy of `media-service` v4.7.0 goes out.
- 09:14 Upload error rate rises from 0.2% to 100%. No alert fires.
- 09:41 First customer support ticket.
- 10:03 An engineer notices the ticket volume and begins investigating.
- 10:20 Investigation identifies v4.7.0's thumbnail generator as the cause: it requires an `ImageMagick` binary absent from the production container image.
- 10:31 Rollback started.
- 10:44 Rollback complete; uploads recover.
- 11:48 Backlog of retried uploads drains; incident closed.

Once the cause was identified, response was quick: 11 minutes from diagnosis to rollback start, 13 minutes to full recovery. The cost of the incident sits almost entirely in the 49 minutes before anyone knew and the 17 minutes of investigation that followed, both of which are detection problems rather than remediation problems.

## Contributing factors

Three things had to line up for a missing binary to become a two-and-a-half-hour total outage. The production container image is built from a different Dockerfile than the one CI uses, so the environment that ran the tests was not the environment that ran the code, and a dependency added to one was never required of the other. The integration suite then mocked the thumbnail generator, which removed the last place the missing binary could have surfaced; the tests exercised our code around the generator but never the generator itself, and passed on an image where it could not run. Finally, the alert measured HTTP status rather than application-level success, so a failure mode that returns 200 was invisible to monitoring by construction. Any one of these alone would have been caught by the others.

The 200-with-error-body response is worth separating out from the alerting gap, because it is a defect in its own right. A request that fails should not return a success status, and the same convention will hide the next failure in this path from every consumer that checks status codes, including client retry logic and any future alerting built on the same signal.

## Action items

Owners and target dates are not filled in below; they need to be assigned before this postmortem is closed.

- Build the production image from the same Dockerfile as CI, or, if separate images are genuinely required, derive both from a shared base that pins runtime dependencies in one place.
- Add a smoke test that runs against the production image and exercises a real upload through real thumbnail generation, with no mocking of the generator.
- Fix the upload endpoint to return an appropriate 5xx status when processing fails, and audit the rest of `media-service` for the same pattern.
- Add an alert on application-level upload success rate, defined independently of HTTP status, with a threshold that would have fired within a few minutes at 09:14.
- Add a post-deploy check on the upload success rate that blocks or automatically reverts a rollout when the rate drops sharply after a deploy.
- Route support ticket volume spikes on a single topic into the on-call channel, so that customer signal reaches engineering faster than the 49 minutes it took here.

Two notes on what I could not determine from the notes provided. The reason the production and CI Dockerfiles diverged is not recorded, and the fix above may be the wrong one if the divergence is deliberate and load-bearing; someone who knows that history should confirm. Nor do the notes say whether the 18,000 failed uploads were all retried successfully after 10:44 or whether some users abandoned the attempt, which matters for whether any customer follow-up is owed.