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
