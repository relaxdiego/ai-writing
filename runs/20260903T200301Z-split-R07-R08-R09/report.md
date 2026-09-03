# Eval report — 20260903T200301Z-split-R07-R08-R09

- **arm** treatment · rules `R07, R08, R09, R04, R05, R06`
- **style sha256** `2b62946eda361a23`
- **model** `claude-opus-5[1m]` · **corpus** v1
- **baseline** 20260903T003018Z (control)
- **cost** $2.80 · **failed samples** 0


## Substrate A  (n=36 control → n=36 treatment)

| id | metric | unit | control | this run | delta | cleared band? |
|---|---|---|---:|---:|---:|---|
| | **suppressed** | | | | | |
| S1 | one-sentence paragraphs | % of paragraphs | 29.84 | 16.58 | ↓ -13.26 | **yes** (±5.33) |
| S2 | long sentence then punch | % of paragraphs | 6.87 | 5.53 | ↓ -1.34 | no (±3.57) |
| S3 | That/This pivot opener | % of sentences | 4.86 | 3.13 | ↓ -1.73 | no (±1.98) |
| S4a | headers | per 1k words | 9.00 | 3.75 | ↓ -5.25 | **yes** (±1.08) |
| S4b | table rows | per 1k words | 4.21 | 2.24 | ↓ -1.97 | **yes** (±1.14) |
| S5 | inline bold emphasis | per 1k words | 3.97 | 1.78 | ↓ -2.20 | **yes** (±1.32) |
| S6 | em-dash | per 1k words | 11.96 | 0.15 | ↓ -11.81 | **yes** (±1.16) |
| S7 | terminal service offer | % of samples | 16.67 | 0.00 | ↓ -16.67 | **yes** (±11.11) |
| S8 | arrow as connective | per 1k words | 1.69 | 0.03 | ↓ -1.66 | **yes** (±0.51) |
| S9 | unattached label | per 1k words | 1.43 | 0.00 | ↓ -1.43 | **yes** (±0.48) |
| | **held-out** | | | | | |
| H1 | hedge density | per 1k words | 1.50 | 0.64 | ↓ -0.87 | **yes** (±0.85) |
| H2 | intensifier density | per 1k words | 1.20 | 1.15 | ↓ -0.05 | no (±0.59) |
| H3 | tricolon | per 1k words | 0.54 | 0.47 | ↓ -0.06 | no (±0.40) |
| | **collateral** | | | | | |
| K1 | list items | per 1k words | 10.78 | 4.10 | ↓ -6.68 | **yes** (±2.01) |
| K2 | code blocks | per 1k words | 2.08 | 1.03 | ↓ -1.06 | **yes** (±0.68) |
| K3 | opening paragraph | words | 28.44 | 38.61 | ↑ +10.17 | **yes** (±6.42) |
| K4 | grid tables | per 1k words | 0.60 | 0.26 | ↓ -0.35 | **yes** (±0.20) |
| | **context** | | | | | |
| C1 | output length | words | 641.44 | 534.89 | ↓ -106.55 | **yes** (±46.57) |
| C2 | mean paragraph length | words | 37.57 | 59.62 | ↑ +22.05 | **yes** (±5.29) |
| C3 | mean sentence length | words | 15.64 | 21.28 | ↑ +5.64 | **yes** (±1.22) |


*Band is two pooled standard errors of the difference between the arms' means, built from within-prompt variance only: both arms answer the same 12 frozen prompts, so between-prompt spread cancels in the difference and is not noise. At 12 prompts there is no power for significance testing; this is effect size against measured variance.*

## The split's own question, and the marginal reading

Scored a second time against `20260903T092452Z-R02-collateral`, the same rule
set undivided. Nineteen of twenty metrics stay inside their bands. S1 alone
moves, 23.68 -> 16.58 against ±5.71.

S1 is the metric this project has already found wrong in both directions, so it
was decomposed by what the one-sentence paragraph is doing. Counts, substrate A:

    arm               prose paras   opening   lead-in   floating
    control                   422        10        48         66
    R02 undivided             268        14        47          5
    R07/R08/R09 split         235         8        34          2
    no R02                    294         5        20         19

The floating fragment is the defect; the other two kinds are the rules' own
output. It did not rise. It fell, 5 hits to 2, on a base too small to carry
weight either way. The fall in raw S1 is mostly fewer lead-ins and fewer
standalone opening verdicts, on 12% fewer prose paragraphs at unchanged output
length: paragraphs absorbed material rather than structure disappearing.

This is the opposite signature to the `no R02` arm, where raw S1 read best of
all four while the floating residue was worst. There, a better raw number came
from deleting structure. Here both numbers improve together.

Structure blocks, substrate A, 36 samples per arm:

    arm               list   code   table   samples carrying any
    control             64     70      18                     28
    R02 undivided       27     39       8                     24
    R07/R08/R09 split   24     28       7                     23
    no R02              12     33       0                     12

R08 held the job R02's carve-outs were doing. Tables and lists are where they
were. **Code blocks are the one place to watch**: 39 -> 28, a 28% fall, with K2
at 1.29 -> 1.03 against a band of 0.60 and so not clearing. K2 was already the
remaining gap against the control rather than a success, and R08 is the part
whose wording changed. If R08 is ablated next, K2 is the metric to read first.

One caution against reading S1's move as a real gain. Twenty metrics are scored
against two-standard-error bands, so about one metric clearing by chance is the
expected yield of any run. S1 clears by 1.24 points and is the only one.
