# Style rules

Each rule is individually addressable by its ID so that ablation can attribute a
metric change to a specific instruction. The assembler emits only the rules it
is asked for; `build/style.prompt.md` is the artifact actually injected, and its
SHA-256 is recorded in every run manifest.

Rules must never name a held-out mannerism (TAXONOMY.md, held-out set).

The assembler emits rules in file order, not in numeric order, and file order is
the order the model reads them in. Where a rule sits is therefore part of the
treatment. IDs are addresses only; they record when a rule was written.

## What each rule is attributed to

Substrate A, the gate. A rule stays only where a run isolates its effect, never
because the stack it sits in cleared.

| rule | owns | evidence |
|---|---|---|
| R07 | S1 corrected, K3 | **inherited, not re-measured.** From R02 undivided: the floating-fragment residue of S1, pooled and uncapped, 19.91 -> 4.48 against 11.22 without R02, in `20260903T193603Z-ablate-R02`; and K3 64.9 -> 36.7 band 12.10 in `20260903T092452Z-R02-collateral` |
| R08 | K1, K2, K4 | **inherited, not re-measured.** From R02's collateral clauses, `20260903T092452Z-R02-collateral`: K1 0.80 -> 4.63 band 1.79, K2 0.86 -> 1.29 band 0.24, K4 0.00 -> 0.27 band 0.11 |
| R09 | S2, S3 — **claimed, not earned** | `20260903T193603Z-ablate-R02` removed R02 undivided and moved S2 by +0.09 against a band of 3.55 and S3 by -1.20 against a band of 1.73. Neither clears. The rule is kept pending its own ablation, not on evidence |
| R10 | S4a, S4b, K4; and K1 as a cost | ablation by replacement, `20260903T231128Z-R10-scan-not-length` against the R04 arm: S4a 3.60 -> 4.35 band 0.43, S4b 1.36 -> 5.64 band 1.80, K4 0.18 -> 0.78 band 0.27, K1 5.94 -> 3.52 band 1.83. Six of twenty metrics cleared where chance yields one. The headings return where they were wanted and the tables overshoot the control |
| R05 | S7 | ablation, `20260903T042140Z-ablate-R05`: removing it returns S7 to 16.67, the control rate exactly, clearing on both substrates |
| R06 | S6 | marginal on R02, `20260903T035059Z-R03-R06`: 8.44 -> 0.97, band 1.04 |

**Two estimators of S1 are in circulation, and a figure is meaningless without
saying which.** The shipped detector averages a per-sample percentage and counts
only sentences of 25 words or fewer. The R02 ablation was argued on a pooled,
uncapped count instead. On the control the two read 29.84 and 35.55. Both
estimators, and both of the other two combinations, rank the arms the same way
in both directions, so the ablation's finding survives the choice; the numbers
quoted for it do not survive being mixed. Where this file gives a corrected S1 it
now says which estimator produced it.

**R07, R08 and R09 are R02 divided, and no run has yet measured them apart.**
Every figure in this file below this line, and every figure in `TAXONOMY.md`,
was measured on R02 undivided and still says `R02`. Those readings are correct
for the runs that produced them and are not rewritten. The three rules carry
R02's text almost unchanged: one sentence was restated so that R08 does not
depend on standing next to R07, and the rest is verbatim. Whether the division
preserves the effect is an open question and the reason for the next run.

The collateral clauses cost S1, S4a and S5, and the S1 cost is smaller than the
metric says. S1 rises 4.76 -> 23.68 and no longer clears against the control. Decomposed by
what the single-sentence paragraph is doing, the defect did not return: a
fragment floating in prose holds at 13 -> 16 of 272 paragraphs, 5.7% -> 5.9%,
against 22.8% in the control. The rise is the clause's own output. Opening
verdicts go 5 -> 14 and lines introducing a restored list or code block go
12 -> 48, against 16 and 50 in the control. S1 counts both as defects because it
cannot see what follows the paragraph. Read S1 with that decomposition until the
detector is split; it is the third estimator fault found, after S2's per-sample
ratio and S4b's row counting.

S4a rises for real and is not an artifact. Headers go 3.44 -> 3.95 against a
band of 0.43, entirely in documents, where conversational headers stay at 0.00
and the control sits at 9.00.

**S5's rise is an artifact, and this corrects the record.** The reading was that
inline bold went 0.27 -> 2.07 against a band of 0.83 and that a ratified defect
had partly come back. It had not. S5 strips a bold that occupies a whole line
but counts a bold that opens a list item, which is preceded by its bullet, and
R06 names that use as permitted. Excluding it, the ruled arms carry **no inline
bold at all**: 2.88 -> 0.00 on v1 and 2.16 -> 0.00 on v2, against controls of
1.52 and 1.16 under the same exclusion. All 37 hits in the v2 ruled arm are
labels opening list entries. What the metric was reporting is R08 restoring
lists, counted as a defect. It is the same fault as S4b, a suppressed metric and
a collateral metric counting the same markup, and it is the fourth estimator
fault found. The detector is unchanged and the ruling belongs to the copyeditor;
`TAXONOMY.md` entry 5 carries the evidence.

**S2 belongs to R02, and R05 never owned it.** The hypothesis that it did was an
artifact of how S2 was counted. S2 averaged a per-sample percentage, so a reply
with 3 paragraphs weighed as much as a document with 30; the arm's real rate is
punch paragraphs over all paragraphs, pooled. Pooling it drops the per-sample
spread from about 17 to about 6 and changes the reading:

    arm             per-sample   pooled
    control               9.38     6.62
    R02 alone             5.54     3.21
    stack without R05     7.64     4.94
    shipped with R05      3.09     3.04

R02 alone clears S2 against the control, 6.62 -> 3.21 against a band of 2.89,
in a run R05 was not in. Ablating R05 from the shipped set moves S2 by +1.89
against a band of 3.32 and clears nothing. Under the old count R02 alone reached
only 5.54 and looked to have failed, which is what made R05 look necessary.

R03 was written for S2 and did nothing; that verdict is unchanged. Substrate B
does not confirm the attribution and does not contradict it either: no arm
separates there at n=3, so S2 on B is unresolved. Substrate A is the gate.

This also retires the noise floor as the way to settle S2, which is what the
floor was last held to be blocking. It settled itself for nothing.

## The word in a rule is not the word in the writing

The copyeditor flagged "shape" twice unprompted in the first blind read, and R09
happened to contain it: "That shape performs insight rather than delivering it."
That made seeding a live hypothesis, and it was cheap to test.

R09 was changed to say "flourish" instead, one word in a 699-word prompt, and
corpus v2 was re-run: `runs/20260903T224835Z-v2-r09-flourish`, style sha
`bb3535a1`, 36 samples, $2.81.

**Seeding is refuted, twice over.** "flourish" appears zero times in the output,
and it had already read zero across 180 earlier samples, so a single hit would
have been signal. Meanwhile "shape" did not fall when the rule stopped saying it.
It rose, 5 hits to 7. Removing a word from the rules did not remove it from the
writing, so the rule was never putting it there. The hits are mostly the verb --
"it shapes the fix", "already shapes what our backups can do" -- and not R09's
noun at all.

"cadence" is the counter-case that makes the point. It is not in the injected
prompt and never has been, and it still climbs across ruled arms: 2 in the v1
control, 6 under the split. Vocabulary moves with the rules without being in
them, so a word appearing more often under instruction is not evidence that the
instruction named it.

**"shape" stays a taxonomy candidate on its own merits.** A reader caught it
twice in twelve samples while the rate is 0.29 per 1,000 words against a control
of 0.19, on counts of four to seven. That gap between what a person notices and
what a rate reports is the DESIGN 4.2b failure mode, not a small effect.

**The rule reads "shape" again.** The arm that passed the blind read is the
"shape" arm, and nothing measurable separates the two, so the shipped set matches
the text that was actually read. Flipping it back is one word and costs nothing.

**A useful by-product: the harness is insensitive to a one-word prompt edit.**
Scored against the arm it was cloned from, zero of twenty metrics cleared their
bands. That is the closest thing to a null run this project has and it is worth
remembering the next time a small edit appears to move something.

## Retired IDs

**R01 — match length to what the question earns.** Withdrawn after
`runs/20260903T030500Z-R01` on the grounds that constraining length cut output by
a third and moved no cadence metric. **That reason was wrong, and the band
correction exposed it.** R01 moves S1 29.84 -> 23.78 against a band of 6.44, and
moves S4a, S4b, S5, K1 and C1 as well. R01 stays retired because R02 is far
stronger on the same metric, 29.84 -> 7.58, and buys it without cutting a third of
the answer away. The withdrawal stands; the stated reason does not, and
TAXONOMY.md's counter-observation that length may be upstream is live again.
**R02 — let a paragraph develop. Divided, not withdrawn.** R02 was 294 words,
48% of the whole rule set, and 68% of it was carve-outs hung on a 37-word core.
`runs/20260903T193603Z-ablate-R02` removed it for the first time and found the
core carrying corrected S1 and the carve-outs carrying the structure metrics,
while S2 and S3 moved inside their bands. The parts were doing different jobs
and could not be addressed separately, so R02 became R07, R08 and R09. **The ID
is retired because the text is no longer one instruction, not because the
instruction failed.** Every historical `--rules R02` label means the undivided
rule and stays unambiguous.
**R03 — do not land the paragraph.** Withdrawn after
`runs/20260903T040710Z-ablate-R03`: ablating it moved S2, its own target, by
+0.10 on substrate A against a band of 3.14, and all eight suppressed metrics
still cleared without it. R02's paragraph-development clause had already taken
the epigrammatic close as far as it goes.
**R04 — reserve structure for structured content. Replaced, not withdrawn.**
R04 decided what may carry a heading by asking how long the writing is: "A reply
of a few hundred words is read once, from the top, and needs neither." The test
is wrong, and reading the samples by prompt shows it failing in the same place
every time. On the pull request description, the one document short enough to
look like a reply, headings go from 6.3 in the v1 control to 0.0 in every arm
R04 appears in -- fifteen of eighteen substrate-A samples across six arms carry
no heading at all and the other three carry one, including the arm where R02 was
ablated and R04 stood without it. Corpus v2 repeats it: 1, 1 and 0 headings
against a control of 5, 5 and 5. Long documents are untouched over the same runs: the ADR holds 4.7 against a
control of 8.3, the postmortem 7.0 against 9.3, the migration guide 8.3 against
11.0. R04 does not flatten documents. It flattens the short one, and a pull
request description is scanned however short it is. The blind read lost its one
document verdict there, on exactly that ground.

The same clause takes a table out of a short reply even where the content is
already a grid. On the inconclusive investigation the control sets four hourly
buckets and their counts as a table, 2.7 rows in v1 and 6 in v2, and every ruled
arm reads 0.0; the reader named that paragraph as the place readability dropped.
R08's table protection does not reach it, because R04 has already ruled the
whole reply out of structure.

**R10 replaces R04 and changes one thing: the discriminator is the use, not the
length.** The conversational suppression R04 earned is deliberately kept --
headings on the conversational prompts stay at 0.0 against a control of 5.0,
4.3 and 3.0, and the reader accepted that twice while complaining about it. The
ID is retired because the instruction now says something different, not because
it failed.

## What R10 measured

`runs/20260903T231128Z-R10-scan-not-length`, corpus v2, substrate A, 36 samples,
$2.99, style sha `daee39bf`. The only change from the arm that passed the blind
read is R04 becoming R10, in the same file position, so nothing about reading
order moved.

**The two faults R10 was written for are both gone.** The pull request
description goes from 0.7 headings to 4.7 against a control of 5.0, and the
inconclusive investigation goes from 0.0 table rows to 6.7 against a control of
4.0. Both were named by the reader, and neither survives.

**The conversational suppression survives untouched.** Headings on all seven
conversational prompts stay at 0.0, against a control that writes 4.3, 5.0, 3.7
and 0.7 on four of them. Replacing the length test did not cost the effect the
length test was hiding behind.

**The table clause overshot, and it is paying for it in lists.** Against the R04
arm, six of twenty metrics cleared their bands where chance yields one:

    S4a  headers          3.60 -> 4.35   band 0.43
    S4b  table rows       1.36 -> 5.64   band 1.80
    K4   grid tables      0.18 -> 0.78   band 0.27
    K1   list items       5.94 -> 3.52   band 1.83
    H1   hedge density    1.45 -> 0.99   band 0.46
    C1   output length     475 ->  548   band 42.81

S4b now sits above the control's 4.60 and K4 above the control's 0.55, so the
grid-table gap the scorecard has carried since the collateral set was written is
not merely closed but overrun. K1 falls in the same run.

**The lists did not vanish; they became tables, and the tables are real grids.**
Set as a list on the control and as a table under R10: five image libraries
against the call that loses orientation and the call that keeps it `[c02-r1]`;
five API changes against whether the codemod fixes them and whether 2.x code
still runs `[d05-r1]`. Both are several things compared across the same
dimensions, which is what both R08 and R10 say a table is for. Counting the two
together, structure per 1,000 words goes 7.30 under R04 to 9.16 under R10,
against a control of 14.66, so about a quarter of the remaining gap closed.

**Whether that trade is an improvement is a question about prose and belongs to
the copyeditor, not to K1.** The metric can only say a list item became a table
row. Tables also appear in three conversational prompts where the control writes
none, which is the part of the overshoot least likely to survive a reading.

Retired IDs are never reused and never assembled, so historical run records stay
unambiguous.

## R07 — Let a paragraph develop

Carry a thought from claim through reasoning to consequence inside a single
paragraph. A paragraph holding one sentence has usually been cut away from the
one before it; join them unless the isolation is doing real work.

An answer that reaches a recommendation, a refusal, or a warning states it first
and by itself, then develops the reasoning behind it. That opening line is not a
paragraph cut away from the one after it, and it is the clearest case of the
isolation doing real work. Where the reader has to act on a danger or choose
between costs, the danger and the cost go in front of the explanation, not after
it.

## R08 — A list, a worked example and a table are not paragraphs

The instruction to develop a paragraph applies to prose only. A list is not a
paragraph that somebody chopped up. Where the content is a set of parallel
items, such as competing explanations, ordered steps, or options to choose
between, set it as a list and leave it as a list. A worked example is the same
case: a code block is the example itself, and absorbing it into the sentences
around it removes the thing the reader came for.

A table is not a paragraph either. Where several things are compared across the
same dimensions, and a reader will want to find one cell, set it as a table and
leave it as one. A timeline, a flag reference, and a before-and-after matrix are
all this case.

## R09 — Do not perform a point you have already made

Do not close a paragraph with a short verdict following a long explanation. That
shape performs insight rather than delivering it, and the explanation has
already carried the point. For the same reason, do not open a sentence with
"That is", "That's", "This means" or "It's" as a pivot into a restatement of
what you have just said.

## R10 — Reserve structure for what a reader will scan

Headings and tables are for writing a reader will scan, search and return to.
What settles that is the use, not the length. A pull request description or a
release note is read by somebody looking for one part of it, so it stays
sectioned however short it runs. A reply inside a conversation is read once,
from the top, however long it runs, and carries its organisation in the prose: a
sentence saying what you are about to take up does the work the heading was
standing in for, and it does it without breaking the page into administered
sections.

Use a table when the content is already a grid: several things compared across
the same dimensions, or figures a reader will want to read off one at a time.
Counts and timings taken out of a log or a benchmark are that case, and running
them into a sentence leaves the reader rebuilding a grid you already had. Two or
three points belong in sentences. A column of labels beside a column of prose is
a list wearing a table's clothes.

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
