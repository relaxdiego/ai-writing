You're right, and I was wrong. Line 33–34 raises immediately for any status below 500 except 429, so a 400 never reaches the `time.sleep` — it propagates on the first attempt. My "narrow the retry condition" advice was solving a problem that doesn't exist; the condition is already narrow.

I did skim it. I saw `except HTTPError` wrapping the sleep-and-loop and pattern-matched to "catches everything, retries everything" without reading the guard inside the handler.

Nothing to change here as far as 400s go.