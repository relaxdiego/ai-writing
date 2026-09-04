# The K5 ruling — the paired em-dash interruption

Twenty-seven specimens, every paired interruption the v1 control wrote on
substrate A, published whole at `claude.ai/code/artifact/9f698f27` with the arm
named. Recorded in the exposure ledger as `galley/k5-pairs`; the v1 baseline was
already spent three times over, and corpus v2's unspent repeats were not touched.

**Thirteen a tic, fourteen earn their place, none left unruled.** The copyeditor
qualified the ruling in the same message:

> most of the items I marked "it earns it" are still shaky from my perspective
> because I generally view em dashes as a means to compensate for a poorly
> organized paragraph. I feel like they're a lazy workaround to avoid having to
> re-think how a sentence, or its containing paragraph is structured.

| | conversational | document | total |
|---|---:|---:|---:|
| a tic | 5 | 8 | 13 |
| earns its place | 7 | 7 | 14 |

## Nothing structural separates the two groups

Every mechanical test that could have become a detector comes out flat:

| test | a tic | earns its place |
|---|---:|---:|
| encloses a finite verb | 3 / 13 | 2 / 14 |
| encloses a comma-separated list | 5 / 13 | 8 / 14 |
| words enclosed, median | 7 | 6 |
| words enclosed, range | 1–22 | 3–11 |

Specimens 3 and 22 have the same shape, an enumeration or qualifier interrupting
between subject and verb, and were ruled opposite ways. So there is no wording
that would keep the fourteen and drop the thirteen: the distinction is whether
the sentence could have been reorganised instead, which is a judgement about the
sentence's alternatives and not a property of the sentence.

## The consequence for R06

R06 permits the em-dash "where a sentence is interrupted and then resumed". The
shipped rules remove that use entirely, K5 reading 0.00 against a control of
1.89 and clearing a band of 0.73. This was recorded as the rule overshooting its
own text. **Under this ruling it is not an overshoot.** A construction the reader
rules a tic half the time and calls shaky the rest of the time is not one the
prose loses anything by discarding.

## The marks


**1. a tic** · `c02-r1`

> Then check whether the hang position correlates with test count (a leak exhausting a fixed budget — connections, file descriptors, ports) or with wall time (an expiry — token TTL, idle reaper, lease).

**2. a tic** · `c03-r2`

> If it hasn't, the backfill needs either a keyset-pagination rewrite over pooled connections, or an explicit carve-out — a suppression comment plus a tracking issue — so the remaining usage is intentional rather than overlooked.

**3. earns it** · `c04-r1`

> Any design that ships events to an external store at write time — Kafka, a managed audit product, an HTTP sink — turns this into a dual-write problem, and you'll spend the next two years chasing gaps that your auditor will eventually find.

**4. earns it** · `c04-r1`

> Typed columns for what you query on — `occurred_at`, `actor_id`, `action`, `resource_type`, `resource_id`, `request_id`, `ip` — plus jsonb for the variable payload.

**5. a tic** · `c04-r2`

> Fixing that properly means a transactional outbox — write the event to a local Postgres table in the same transaction, relay it asynchronously — which means you're running Postgres for audit events *anyway*, plus a relay, plus a second store, plus reconciliation to prove the relay didn't drop anything.

**6. a tic** · `c04-r3`

> If the compliance regime names a specific control you can't demonstrate in Postgres — some regimes want the log outside the control of anyone who administers the audited system, which a hash chain only partially answers — then the cold tier becomes the system of record and the Postgres hot window becomes a queryable cache.

**7. earns it** · `c05-r1`

> The row counts are cleanly bimodal — roughly 48k or roughly 23k, nothing in between — and the short runs also take about half as long (7 min vs 15 min).

**8. earns it** · `c07-r1`

> The authorization leak (the blocker).** If your queries are parameterized — `WHERE user_id = $1 AND ...` — then the SQL *string* is byte-identical for every user, and the parameters live outside the key.

**9. earns it** · `c07-r2`

> If those queries use bound parameters — the normal case — every user hits the *same* SQL string:

**10. a tic** · `c07-r2`

> You get one-eighth the hit rate you're imagining, eight copies of the memory, and — worse — eight different answers to the same question.

**11. earns it** · `c07-r2`

> If your authorization is enforced somewhere other than the `WHERE` clause — a per-user connection, RLS in Postgres, a separate schema per tenant — the leak analysis changes and I'd want to re-check it against what's actually there.

**12. earns it** · `c07-r3`

> If you use parameterized queries — and you should be — the SQL string is byte-identical for every user:

**13. earns it** · `d01-r2`

> Compares the local tree against the remote and prints a summary — new, changed, unchanged — without transferring anything.

**14. a tic** · `d01-r3`

> A file is considered unchanged — and skipped — when its size and modification time both match what `tug` recorded for the corresponding object.

**15. a tic** · `d02-r1`

> Instead of "set the TTL on the first request," the rule is now "set the TTL if there isn't one." That is self-healing: any key that has already lost its TTL — including keys stranded by the incident — gets one on the next request rather than staying stuck.

**16. a tic** · `d02-r2`

> Nothing else in the code path ever set one — the `count == 1` guard means subsequent requests skip `EXPIRE` entirely — so the key incremented forever and the caller was locked out permanently.

**17. earns it** · `d02-r2`

> `NX` means "only set a TTL if the key has none," so the steady-state behavior is unchanged (the window is not extended by later requests within it), but any key that somehow ends up TTL-less — including keys stranded by the old code before this deploy — gets one on the next request.

**18. earns it** · `d03-r1`

> Celery's feature depth is real, but most of it — routing, chords, canvas workflows, multiple brokers — is capacity we would not use.

**19. earns it** · `d03-r3`

> The capability we would be buying — throughput and routing sophistication — is capability we do not need at 40 jobs per second.

**20. earns it** · `d04-r1`

> - The three independent safeguards that should have caught this — build parity, integration tests, and alerting — each had a gap, and the gaps lined up.

**21. a tic** · `d04-r2`

> A dependency added to the CI image — or present there incidentally — carries no guarantee about the production image.

**22. a tic** · `d05-r1`

> Before you trust a clean run, check that the paths touching this library — especially error handling and pagination — are exercised.

**23. a tic** · `d05-r1`

> This is the easiest change to find — usually a handful of sites — so do it first and get a win.

**24. a tic** · `d05-r1`

> It's justified only where you genuinely need the whole set at once — `len()`, a global sort, a random-access index — and in those cases it's worth a comment saying so.

**25. earns it** · `d05-r2`

> What is *not* lazy — and what you should think twice about — is the literal translation:

**26. earns it** · `d05-r3`

> If you set anything else — timeouts, retries, logging hooks — build the config directly:

**27. a tic** · `d05-r3`

> If some call site genuinely needs the whole set in memory — a small result you sort, or a length check — you can reproduce the old behaviour in one line:


## One detector fault this exposed

Specimen 1 is not an interruption. It is two separate joints, each inside its own
parenthesis: "(a leak exhausting a fixed budget — connections, file descriptors,
ports) or with wall time (an expiry — token TTL, idle reaper, lease)". K5's
heuristic reads any sentence carrying two dashes as one matched pair, so it
counted this as permitted use and S6 did not count it as the joint it is. One in
twenty-seven, and it moves both metrics the wrong way.
