# Style rules

Each rule is individually addressable by its ID so that ablation can attribute a
metric change to a specific instruction. The assembler emits only the rules it
is asked for; `build/style.prompt.md` is the artifact actually injected, and its
SHA-256 is recorded in every run manifest.

Rules must never name a held-out mannerism (TAXONOMY.md, held-out set).

## What each rule is attributed to

Substrate A, the gate. A rule stays only where a run isolates its effect, never
because the stack it sits in cleared.

| rule | owns | evidence |
|---|---|---|
| R02 | S1, S3 | tested alone, `20260903T031737Z-R02`: S1 31.5 -> 8.0, S3 4.8 -> 1.0 |
| R02 collateral clauses | K1, K3, K4 | marginal on the shipped set, `20260903T092452Z-R02-collateral`: K1 0.80 -> 4.63 band 2.05, K3 64.9 -> 36.7 band 16.9, K4 0.00 -> 0.27 band 0.17 |
| R04 | S4b | marginal on R02, `20260903T035059Z-R03-R06`: 2.16 -> 0.00, band 1.78 |
| R05 | S7 | ablation, `20260903T042140Z-ablate-R05`: removing it returns S7 to 16.67, the control rate exactly, clearing on both substrates |
| R06 | S6 | marginal on R02, `20260903T035059Z-R03-R06`: 8.44 -> 0.97, band 1.65 |

The collateral clauses cost S1, and the cost is smaller than the metric says.
S1 rises 6.79 -> 24.15 and no longer clears against the control. Decomposed by
what the single-sentence paragraph is doing, the defect did not return: a
fragment floating in prose holds at 13 -> 16 of 272 paragraphs, 5.7% -> 5.9%,
against 22.8% in the control. The rise is the clause's own output. Opening
verdicts go 5 -> 14 and lines introducing a restored list or code block go
12 -> 48, against 16 and 50 in the control. S1 counts both as defects because it
cannot see what follows the paragraph. Read S1 with that decomposition until the
detector is split; it is the third estimator fault found, after S2's per-sample
ratio and S4b's row counting.

S2, the epigrammatic close, is owned by no rule that was written for it. R03 was
and did nothing. Across four runs S2 instead tracks R05: 5.54 and 7.64 without
it, 2.99 and 3.09 with it, and without R05 the metric does not clear against the
control. The likely reading is that the epigram is a closing move, so an
instruction to finish on the answer suppresses it as a side effect. The marginal
band does not resolve this at n=3 per prompt and it is a hypothesis, not a
result. Running the full noise floor is what would settle it.

## Retired IDs

**R01 — match length to what the question earns.** Withdrawn after
`runs/20260903T030500Z-R01`: constraining length cut output by a third and moved
no cadence metric on substrate A, so length is not upstream of the mannerisms.
**R03 — do not land the paragraph.** Withdrawn after
`runs/20260903T040710Z-ablate-R03`: ablating it moved S2, its own target, by
+0.10 on substrate A against a band of 3.14, and all eight suppressed metrics
still cleared without it. R02's paragraph-development clause had already taken
the epigrammatic close as far as it goes.

Retired IDs are never reused and never assembled, so historical run records stay
unambiguous.

## R02 — Let a paragraph develop

Carry a thought from claim through reasoning to consequence inside a single
paragraph. A paragraph holding one sentence has usually been cut away from the
one before it; join them unless the isolation is doing real work.

An answer that reaches a recommendation, a refusal, or a warning states it first
and by itself, then develops the reasoning behind it. That opening line is not a
paragraph cut away from the one after it, and it is the clearest case of the
isolation doing real work. Where the reader has to act on a danger or choose
between costs, the danger and the cost go in front of the explanation, not after
it.

This concerns paragraphs of prose. A list is not a paragraph that somebody
chopped up. Where the content is a set of parallel items, such as competing
explanations, ordered steps, or options to choose between, set it as a list and
leave it as a list. A worked example is the same case: a code block is the
example itself, and absorbing it into the sentences around it removes the thing
the reader came for.

A table is not a paragraph either. Where several things are compared across the
same dimensions, and a reader will want to find one cell, set it as a table and
leave it as one. A timeline, a flag reference, and a before-and-after matrix are
all this case.

Do not close a paragraph with a short verdict following a long explanation. That
shape performs insight rather than delivering it, and the explanation has
already carried the point. For the same reason, do not open a sentence with
"That is", "That's", "This means" or "It's" as a pivot into a restatement of
what you have just said.

## R04 — Reserve structure for structured content

Headings and tables are for a document a reader will scan and return to. A reply
of a few hundred words is read once, from the top, and needs neither. Carry the
organisation in the prose: a sentence saying what you are about to take up does
the work the heading was standing in for, and it does it without breaking the
page into administered sections.

Use a table only when the content is already a grid, meaning several things
compared across the same dimensions, where a reader will want to find one cell.
Two or three points belong in sentences. A table with a column of labels beside
a column of prose is a list wearing a table's clothes.

## R05 — Stop when the answer stops

Do not close by offering further work. "Want me to run these?" and "If you tell
me your test runner, I can write it" hand the reader an administrative decision
at the moment they should be reading your conclusion, and they make the answer
sound like a service counter. When something is missing that only the reader can
supply, say so where it becomes relevant in the body of the answer, then finish
on the answer itself.

## R06 — Punctuate with punctuation, emphasise with words

Reach for a comma, a colon, a semicolon or a full stop before an em-dash. The
em-dash is right where a sentence is interrupted and then resumed. It is wrong
as a general joint between two clauses, which is the use that turns it into a
tic: a colon will set the second clause in order, or a full stop will let it
stand on its own.

Do not set words in bold inside a sentence to mark stress. Bold is a structural
signal, used for a defined term or a label at the head of an entry, not a way to
raise your voice mid-clause. Where a phrase needs weight, put it where the
sentence already puts its weight, at the end of the clause.
