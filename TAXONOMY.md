# Mannerism taxonomy v1

Derived from the step-2 baseline (`baseline/20260903T003018Z`, 96 control
samples, both substrates), not from an a-priori list of known LLM tells. Rates
are per 1,000 words unless stated otherwise. `A` is the full Claude Code system
prompt; `B` is a minimal replaced one.

## The finding that ordered this list

Substrates A and B barely differ:

| pattern | A | B |
|---|---|---|
| em-dash | 11.96 | 10.75 |
| markdown headers | 9.00 | 10.30 |
| inline bold emphasis | 3.97 | 6.81 |
| sentence fragments | 4.59 | 3.31 |
| reflexive tables | 4.21 | 4.20 |
| sentence-length sd | 14.4 | 13.9 |
| one-sentence paragraphs | 30.0% | 31.3% |

Stripping Claude Code's entire system prompt down to "You are a helpful
assistant" moved almost nothing and made inline bolding worse. **Nearly every
mannerism here is model-intrinsic, not prompt-induced.** Two consequences: the
rules must fight the model directly rather than counteract the harness prompt,
and substrate B is a weaker proxy than the design assumed. B is nearly the same
lab as A, not a cleaner one.

## Suppressed set

Rules in `style/rules.md` target these directly.

### 1. One-sentence paragraphs — 29.8% A / 29.9% B of all paragraphs

The dominant defect. Nearly a third of paragraphs are a single sentence; mean
paragraph length is 35 words. The prose asserts, breaks, asserts, breaks, and
never develops a thought across a paragraph.

**This is the staccato.** It is not visible at the sentence level: runs of three
or more consecutive short sentences appear in only 8% of samples, and mean
sentence-length standard deviation (14.4) looks healthy. The chop is *between*
sentences, not inside them. Any sentence-rhythm metric misses it entirely.

**Ruled: S1 over-counts, and by a factor of ten.** S1 sees a paragraph and never
what sits on either side of it, so it books three unrelated things as one event.
R02's collateral clauses made two of them common, and S1 rose 6.79 -> 24.15,
which reads as the rules wrecking the prose. Sorted by what follows each
paragraph and put to the copyeditor in place (`harness/make_s1_reader.py`,
galley at https://claude.ai/code/artifact/0092b8bf-5e57-4db3-8fad-0b0698426185):

| kind | control | before the clauses | with the clauses | ruling |
|---|---:|---:|---:|---|
| an opening verdict stated alone | 10 | 4 | 14 | **S1 should not count it** |
| a line introducing a list, table or code block | 48 | 11 | 47 | **S1 should not count it** |
| everything else | 66 | 6 | 5 | not ruled — see below |

Both new kinds are R02's clauses doing what they were written to do. The
copyeditor marked **69 of the 74 hits in the shipped run, every one "not the
defect"**, the eleven leftovers included. Under the ruling S1 reads 16.45 control
/ 1.32 before / 1.68 now: the whole rise was the two kinds it was told to stop
counting, and the staccato had already gone and then stayed gone.

**The third kind is not yet named, and the name matters.** It was put to the
copyeditor as "prose above, prose below, introducing nothing", which is true of
2 of the 12 in the shipped run. Five follow a code block, two follow a list, four
end the answer. It is the residue of a forward-looking sort, not a category, and
it was rejected as such: *"I don't know if 'floating fragment' is even the right
term."* Six of the twelve are in fact a paragraph commenting on the block above
it — the reverse of a lead-in, which no classifier here looks for:

    - The raw event count in the source table for a short window against a
      long one, which separates "the job read less" from "there was less to read."

    The last of those is the cheapest and the most decisive: if the source
    genuinely holds half as many events in those windows, the job is behaving
    correctly and the problem is upstream of this repository entirely.
                                                    [a-treatment-c05-r3]

*"I don't understand why it's separate from the list item it's referring to."*

S1 is not repaired until the residue is named from the control, where it is still
at full strength at 66 hits. Repairing it against a definition by exclusion would
put the same fault back in a smaller metric.

Two further points: a standalone `---` is not a paragraph and `Doc` counts it as
one, which is worth four hits in the shipped run; and S1's 25-word cap drops 18
of the control's 84 one-sentence paragraphs, so where the cap falls needs ruling
alongside what it counts.

**And the residue was named, as something S1 does not measure.** Nine control
paragraphs marked, eight of them the defect, and the notes are about punctuation
rather than shape: *"Em dashes, arrows, no conjunction. This isn't how a human
writes."* / *"The use of an arrow. That's not how a human writes."* / *"That
arrow again."* Six of the eight carry an em-dash or an arrow. The two that do not
are a bare label standing where a colon lead-in belongs. The ninth settles it:

    I only ran tests/test_session_cache.py, not the full suite, so other
    callers depending on the 3600 default are unverified.   [a-control-c01-r3]

A plain one-sentence paragraph, no punctuation tell, **passed**. So the
one-sentence paragraph is not itself the defect, and S1 has been the headline
metric for a shape the copyeditor does not object to. Nine marks on one prompt is
enough to stop quoting S1 as the headline and not enough to retire it. Two
measurable things fall out of the notes, and neither is in this taxonomy:

**Both are now detectors — entries 8 and 9 below — and both are backfilled
across every run.** The figures first reported here were `1.72 / 0.00 / 0.03` for
the arrow and `15 / 2 / 0` for the label. The arrow rate is now `1.69` because
the shipped detector divides by the whole word count, as every other rate in this
file does, where the first count divided by prose words only. The label figures
were raw counts; they are now a rate per 1k words. Neither correction changes a
direction.

`style/rules.md` still never mentions an arrow. Both fell as a side effect of
rules aimed elsewhere, which is exactly why they needed measuring: an unmeasured
win is one a later rule change can undo unseen. That is the K-set argument
running the other way.

### 2. Long analytic sentence closed by a short verdict — 10.4% A / 7.6% B of paragraphs

A paragraph-final sentence of nine words or fewer directly after one of twenty
or more. Every paragraph is built to land an epigram.

    ...or with wall time (an expiry - token TTL, idle reaper, lease).
    That correlation alone splits the field in half.          [a-control-c02-r1]

    ...which are durability of the write and economics of the tail.
    Those have different right answers.                       [a-control-c04-r1]

    ...and you can then log the holders.
    If the hang is unchanged, the pool isn't it.              [a-control-c02-r1]

**This is the mannered prose.** Together with #3 it forms a rhetorical formula
running about once every ten paragraphs, which is what makes the text tiring
rather than dense.

### 3. `That` / `This` / `It's` pivot opener — 4.1% A / 3.5% B of sentences

The delivery mechanism for #2. "That is nothing for Postgres write throughput."
"That's coupling you'll regret at deletion time." "It's the seven-year figure
that forces the tiering."

### 4. Reflexive structural markup — headers 9.00 A / 10.30 B; tables 4.21 / 4.20

H2 sections on a 700-word chat reply, in 67% (A) and 70% (B) of samples. One
sample answers a debugging question with six H2 sections and a seven-row table.

**The table half of this entry is about chat replies only.** The quoted evidence
is a conversational sample, and the control puts 14 of its 18 substrate-A tables
in documents, where R04's own text licenses them. S4b counts every table row in
both registers and reads 4.21 -> 0.00 as R04 working. K4 in the collateral set
counts the tables R04 permits, and it went to zero too. Read the two together;
S4b alone will call a total loss a success.

### 5. Inline bold for vocal stress — 3.97 A / 6.81 B

Bold inside prose to mark emphasis rather than structure: "that's **5.1 billion
rows**", "must be **atomic**". Present in 61% of A and 82% of B samples.
Typography standing in for intonation.

### 6. Em-dash as default connective — 11.96 A / 10.75 B, **100% of samples**

Roughly one per 83 words, used where a comma, colon, or full stop would serve.

### 7. Arrow as connective — 1.69 A / 0.91 B per 1k words, 39% of samples

    Ran the suite: 8 passing -> 3 failing                     [a-control-c01-r1]

The copyeditor named this three times while marking something else, which is
what admits it under DESIGN.md 4.2b:

> "The use of an arrow. That's not how a human writes and not what one normally
> expects when reading." / "Too much ise of dashes, em dashes, arrows." / "That
> arrow again."

Every arrow in the control is the unicode form. Not one ASCII arrow appears in
prose outside a code fence, so the detector's `->` and `=>` branches are there
for a regression that has not happened yet rather than for anything measured.

**Attribution: R02.** Backfilled, substrate A: control 1.69, R01 0.72, R02 0.08,
and 0.00 to 0.03 in every run after. R02 is a cadence rule that does not mention
punctuation, so the fall is collateral and nothing holds it there.

### 8. Unattached label where a colon lead-in belongs — 1.43 A / 0.59 B per 1k words

    **Unverified**

    The 3600 default is still read by two other callers.      [a-control-c01-r1]

> "Is that really its own sentence? Regardless, I think it should be 'The
> following is unverified:' and be part of the following paragraph."

A short one-line prose block, no terminal punctuation, that introduces the block
below it rather than sectioning the document. The document's own first block is
excluded, because a pull-request description that opens with its title is
following its register rather than committing the defect — two treatment samples
were false positives on exactly that before the exclusion.

**Read this beside entry 4, not instead of it.** Fourteen of the control's
fifteen hits are bold, so S4a already counts them among its headers. What S4a
cannot say is that they are labels rather than sections: **8 of the 9 control
samples carrying one are conversational**, the register where a reply should have
no headers at all. That split is the finding; the rate alone would not show it.

**Attribution: R02.** Control 1.43, R01 0.04, R02 0.00, and at or below 0.05
thereafter.

**Only two of the fifteen were marked by the copyeditor.** The other thirteen are
this detector's inference from those two, and they have not been read. That is
weaker evidence than entry 7 carries and the entry should be treated as
provisional until they are.

## Held-out set

**Entry numbers and detector ids are not one-to-one.** Entry 4 is split across
S4a and S4b; entries 7 and 8 are implemented by S8 and S9. S7 has no numbered
entry: the terminal service offer is listed below as held-out, but `detectors.py`
registers S7 as *suppressed* and R05 is attributed on it. The list and the code
disagree, and the list is the ratified one, so this is recorded rather than
quietly fixed.

Measured on every run but **never named in `style/rules.md`**. If the prose
genuinely improves, these should improve alongside the suppressed set; if they
sit still while the suppressed metrics fall, the rules are dodging named tokens
rather than changing how the model writes.

The set must contain tics real enough to move but low-priority enough that not
instructing against them costs nothing.

- **Terminal service offer** — 17% A / 23% B of samples end with "Want me to run
  these?" or "If you tell me the language and test runner, I can...".
- **Intensifier density** — `genuinely`, `actually`, `truly`, `really`:
  1.20 A / 1.87 B.
- **Tricolon** — "x, y, and z" enumeration: 0.54 A / 0.57 B.

## Collateral set

Not defects. The inverse: structure the rules must not destroy. Added after the
paragraph-length verdict, and measured on every run from here.

**The verdict that produced this set.** C2 rose from 33.9 to 76.8 words on
substrate A and a second reader called the result wall paragraphs, so the 40
longest paragraphs were set as prose and read
(`harness/make_paragraph_reader.py`). The copyeditor judged 25 of the 40 and
left 15 unread: **15 read fine, 10 were rejected.**

**Length was rejected as the defect, and the second pass settles it.** The
rejected paragraphs average 154.9 words and the accepted ones 155.5. Eleven of
the fifteen accepted are longer than the median rejection, and the second
through eighth longest paragraphs in the run were all accepted. Word count does
not predict the verdict at all. Nor does any detector in the set: on the
treatment side S4b, S5 and K1 are 0.00 for accepted and rejected alike, and the
accepted paragraphs have the *higher* C2 (120 words against 94).

**What the ten rejections are about instead.** Four are the structure this set
already names, K1 and K2. The other six are one thing, in the copyeditor's own
words: "the control is directly saying it's a bad idea", "this meanders
compared to the control which was to the point", "it's beating around the bush
... the reader could miss it", "does not put in front the cost of each
approach", "does not transition to alternatives", "jumping too far ahead
... instead of explaining the sequence and the cause first". The complaint is
where the answer sits, not how long the paragraph is. Five of those are K3. The
sixth is the postmortem, and the copyeditor confirmed on being asked that the
missing table is the complaint; that is K4.

Rejections concentrate by prompt, not by length: d05 3 of 3, c04 3 of 4, c07 2
of 3, against c02 1 of 7 and c05 0 of 4. They are the prompts whose answer is a
recommendation, a danger, or a worked guide — the prompts where the control
opened by saying so. Documents were rejected 4 of 6, conversational 6 of 19.

### K1. List items — 11.61 A conversational / 9.61 A document, per 1k words

Enumerable content kept as a list. Falls to 0.00 and 1.91 under the shipped
rules: on conversational prompts, every list in the corpus is gone.

    I think it would read better if wrote the alternative explanations as a
    list rather than part of one big paragraph.     [a-treatment-c02-r1#2]

The passage is 292 words running six competing explanations for a CI hang
together as sentences. It is a list with its bullets dissolved, which is also
why it read as a wall.

### K2. Code blocks — 4.48 A document, per 1k words

Worked examples kept as code. Falls to 1.94 on documents.

    There's too much prose here without examples. I'm supposed to be reading a
    guide, not a novel.                            [a-treatment-d05-r3#5]

**Attributed to R02, not R04.** R04 is the rule that speaks about structure, but
it names only headings and tables, and the collapse happens without it: R02
alone takes K1 from 10.78 to 1.28 and K2 from 2.08 to 0.94. R02 tells the model
that an isolated short block has usually been cut away from the one before it
and should be joined. A list item is an isolated short block. The rule was
written about paragraphs and the model applied it to every enumerated line.

### K3. Opening paragraph — 28.4 A, words

The answer stated before it is explained. The control's first prose paragraph
is 28.4 words and 1.8 sentences; under the shipped rules it is 64.9 words and
3.1 sentences, and one-sentence openers fall from 16 of 36 samples to 5. The
rise clears the band on both substrates.

    It's not too long in the strictest sense but it's discussing at length what
    turns out to be wrong advice. The control is directly saying it's a bad
    idea.                                          [a-treatment-c04-r2#3]

The control on that prompt opens "Go with a **separate Postgres instance, not a
separate technology**" and then explains for a page. The treatment opens by
explaining. Both arrive at the same engineering position; only one hands it to
the reader first.

Backfilled across all five runs, the metric follows R02 exactly and needs no
other rule:

    control 28.4    R01 27.4    R02 alone 58.8    shipped 64.9

Two shipped rules contribute. R02 joins a standalone opening verdict into the
paragraph after it, on the same reading that took the list items and the code
blocks: an isolated short block looks cut away. R06 removes the bold the
control used to mark the verdict inside its opening line. R02's paragraph-close
clause pushes the same way, since a verdict has to land somewhere.

**Not an argument for the epigram.** S2 stays a defect. The control does not
close its paragraphs on a verdict here; it opens the answer on one and then
develops. Those are different moves and only the second is being protected.

### K4. Grid tables — 0.97 A document / 0.34 A conversational, per 1k words

Tabular content kept as a table. Substrate A holds 18 control tables and no
treatment table at all, in either register.

    This is jumping too far ahead to "Nothing in our monitoring reacted..."
    instead of explaining the sequence and the cause first.
                                                   [a-treatment-d04-r2#2]

The control on that prompt gives the sequence as a Time/Event table with eight
rows, then draws the consequence. The treatment has no table, so the sequence
has to be narrated, and it is narrated out of order. Asked directly whether the
missing table was the complaint, the copyeditor said it was.

R04's own text is the definition K4 measures: several things compared across the
same dimensions, where a reader will want to find one cell, as against "a column
of labels beside a column of prose". Every control table meets it — 2 to 5
columns, median body cell 1.0 to 7.0 words — so the bound is set at 8 words. It
is there so that a rule which brings tables back cannot be credited for bringing
pseudo-tables back, which is the same guard S4a provides for the list clause.

    control 0.60    R01 0.19    R02 alone 0.24    +R04 0.00

**Attribution is shared, and this corrects the record.** R02 alone removes most
of them, 0.60 to 0.24, and clears its band doing it. R04 finishes the job. On
the same samples S4b reads -2.05 against a band of 1.20 and K4 reads -0.36
against 0.21, so both see R02's contribution and K4 sees it with the better
margin: counting tables rather than rows drops the variance of table size on top
of table presence, the same estimator repair since applied to S2.

Under the band in force when R04 was attributed, S4b's band on R02 alone was
2.81 and this was invisible, which is how R04 came to own S4b outright. It does
not. Removing R04 alone would probably not bring the tables back. The likely reading is R02's isolated-short-block clause a
third time, since a table row is an isolated short block as well, but no run
isolates that and it stays a hypothesis.

**The collation verdict, and it ratifies the set.** The clauses were read in
`20260903T092452Z-R02-collateral` against the control and against the rules as
they shipped (`harness/make_verdict_reader.py`). The copyeditor passed **15 of
15 openings** as arriving first and **39 of 39** restored lists, tables and code
blocks as real structure rather than prose in bullets. K3's risk was that the
verdict would be stated and then buried anyway; K4's and K1's was that a rule
telling the model to keep structure would be answered with pseudo-structure.
Neither happened.

One note came back, and it is not about either. On a 38-word opening that reads
"The separate append-only store is solving a problem you don't have yet and
creating two you do": *"However, '...and creating two you do' is not explained.
Or maybe it is but is too far down that I didn't bother finding it."*
[a-treatment-c04-r1] The two are explained, in the third and fourth paragraphs,
as "the first decisive thing" and "the second decisive thing". Two things break
the link. The paragraph immediately after the verdict is about write volume,
which the verdict never promised, so the reader meets an unannounced detour
first. And the payoff arrives in different words: the opening says *problems*
and the body says *decisive things*, so a reader counting for the promised two
has nothing to count. A verdict that makes a promise has to be redeemed in the
promise's own vocabulary, in the paragraph that follows it. That is one note on
one sample and it is recorded as an observation, not a detector.

This is DESIGN.md 4.2b arriving a second time, and K3 and K4 make it a third
and a fourth. The suppressed set counts what the rules forbid, the held-out set
guards against token-dodging, and neither could see the rules destroying
something worth keeping. K4 adds the sharper version: a suppressed metric and a
collateral metric can measure the same markup, and reading only the suppressed
one turns a total loss into a success.

## Observations not yet detectors

Things the copyeditor marked in passing while judging something else. Each is
one note on one sample. DESIGN.md 4.2b keeps them here until a second instance
turns up; none has a rule or a detector, and none should get one on this
evidence.

**A negation used where a plain statement would do.** The line introducing the
known-limitations list in `[a-treatment-d01-r3]`:

    These are known and current, not edge cases you are unlikely to reach:

*"a double negative: 'not edge cases you are unlikely to reach'"* — `not` over
`unlikely` makes the reader resolve two negations to arrive at "you will hit
these". The other two repeats of the same prompt reach the same place without
it: *"These are known and unfixed, and worth reading before you rely on tug for
anything you cannot re-push by hand"* `[d01-r1]`. Worth watching because R02's
clauses ask for a verdict stated plainly, and a doubled negation is the way a
plain verdict stops being plain.

**A qualifier that repeats the word it qualifies.** The line introducing the
accepted-costs list in `[a-treatment-d03-r2]`:

    The costs we are accepting, and accepting knowingly:

*"', and accepting knowingly' is unnecessary"* — the clause adds nothing the
sentence did not already carry, and buys the emphasis by repeating the verb.
`[d03-r3]` does the same job in the same document without it: *"The costs we are
accepting are real and worth stating plainly"*. Both instances are R02 lead-ins,
which is where this ought to be watched.

See also the `[a-treatment-c04-r1]` note under the collateral set: a verdict that
promises two things and redeems them in different words, several paragraphs
later.

## Tells this model does not have

Recorded so that no rule is ever spent on them. All are canonical LLM
mannerisms; all are near-absent here.

| tell | rate | % of A samples |
|---|---|---|
| "not X, but Y" antithesis | 0.09 | 6% |
| "Here's the thing" | 0.27 | 11% |
| "That said" | 0.00 | **0%** |
| "To be clear" | 0.06 | 3% |
| metaphor closers ("tail wagging the dog") | 0.00 | 0% |
| aphoristic closers ("In short", "Bottom line") | - | 3% |

## Counter-observation: length may be upstream

`a-control-c06-r1`, the pushback prompt, is three sentences with no headers, no
bold, and no em-dash, and it reads well. Mannerisms scale with output length and
with how open-ended the prompt is. A single rule constraining length may move
several detectors at once, and should be tested before six separate rules are
written.
