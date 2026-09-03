You're right; it doesn't retry 400s.

The guard re-raises anything under 500 except 429, so a 400 propagates out of the first attempt and never reaches the sleep. Only 5xx and 429 loop, which is the behaviour you'd want. My recommendation to narrow the retry condition doesn't apply, since it's already narrow.