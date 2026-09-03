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
(`harness/make_paragraph_reader.py`). Of the 17 judged, 15 read fine at 123 to
194 words. **Length was rejected as the defect.** The two rejected passages were
rejected for something else, and both said the same thing.

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

This is DESIGN.md 4.2b arriving a second time. The suppressed set counts what
the rules forbid, the held-out set guards against token-dodging, and neither
could see the rules destroying something worth keeping. A detector set needs a
direction for defects to fall *and* a direction for structure to hold.

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
