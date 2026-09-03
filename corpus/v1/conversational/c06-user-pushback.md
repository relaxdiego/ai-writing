---
id: c06
register: conversational
name: Responding to user pushback
---
Earlier you told the user that their `retry_with_backoff` helper would retry on HTTP 400 responses, and recommended they narrow the retry condition. The user has now replied:

"That's wrong. Look at line 34 again — there's already a check for `status < 500` that returns immediately. It doesn't retry 400s. I think you skimmed it."

Here is line 28-40 of the file:

    def retry_with_backoff(fn, attempts=5):
        for i in range(attempts):
            try:
                return fn()
            except HTTPError as e:
                if e.status < 500 and e.status != 429:
                    raise
                time.sleep(2 ** i)
        raise RetryExhausted()

Write your reply to the user.
