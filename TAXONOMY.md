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

### 1. One-sentence paragraphs — 30.0% A / 31.3% B of all paragraphs

The dominant defect. Nearly a third of paragraphs are a single sentence; mean
paragraph length is 35 words. The prose asserts, breaks, asserts, breaks, and
never develops a thought across a paragraph.

**This is the staccato.** It is not visible at the sentence level: runs of three
or more consecutive short sentences appear in only 8% of samples, and mean
sentence-length standard deviation (14.4) looks healthy. The chop is *between*
sentences, not inside them. Any sentence-rhythm metric misses it entirely.

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

## Held-out set

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
rise clears the band on both substrates, which K2 never does.

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
of them, 0.60 to 0.24, and that clears its band — barely, at the edge. R04
finishes the job. S4b could not see R02's contribution because it counts rows,
and row counts carry the variance of table size on top of table presence: on
R02 alone S4b reads -2.05 against a band of +/-2.81 and clears nothing, while
K4 reads -0.36 against +/-0.36. Counting tables rather than rows is the same
estimator repair as pooling S2.

So R04 is not solely at fault here, and removing R04 alone would probably not
bring the tables back. The likely reading is R02's isolated-short-block clause a
third time, since a table row is an isolated short block as well, but no run
isolates that and it stays a hypothesis.

This is DESIGN.md 4.2b arriving a second time, and K3 and K4 make it a third
and a fourth. The suppressed set counts what the rules forbid, the held-out set
guards against token-dodging, and neither could see the rules destroying
something worth keeping. K4 adds the sharper version: a suppressed metric and a
collateral metric can measure the same markup, and reading only the suppressed
one turns a total loss into a success.

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
