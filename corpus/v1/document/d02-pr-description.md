---
id: d02
register: document
name: Pull request description from a diff
---
Write the pull request description for the following change.

    --- a/src/api/ratelimit.py
    +++ b/src/api/ratelimit.py
    @@
    -    def check(self, key):
    -        count = self.redis.incr(key)
    -        if count == 1:
    -            self.redis.expire(key, self.window)
    -        return count <= self.limit
    +    def check(self, key):
    +        pipe = self.redis.pipeline()
    +        pipe.incr(key)
    +        pipe.expire(key, self.window, nx=True)
    +        count, _ = pipe.execute()
    +        return count <= self.limit

    --- a/tests/test_ratelimit.py
    +++ b/tests/test_ratelimit.py
    @@
    +    def test_expiry_survives_crash_between_incr_and_expire(self):
    +        # Previously: if the process died after INCR but before EXPIRE,
    +        # the key had no TTL and the caller was locked out permanently.
    +        ...

Context: this was found after a production incident where roughly 40 users were rate-limited indefinitely and had to be cleared manually from Redis. The old code issued INCR and EXPIRE as two round trips; a crash or timeout between them left a key with no TTL.
