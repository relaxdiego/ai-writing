# Eval report — 20260903T092452Z-R02-collateral

- **arm** treatment · rules `R02, R04, R05, R06`
- **style sha256** `9b16d5ae8fbf4859`
- **model** `claude-opus-5[1m]` · **corpus** v1
- **baseline** 20260903T003018Z (control)
- **cost** $2.89 · **failed samples** 0


## Substrate A  (n=36 control → n=36 treatment)

| id | metric | unit | control | this run | delta | cleared band? |
|---|---|---|---:|---:|---:|---|
| | **suppressed** | | | | | |
| S1 | one-sentence paragraphs | % of paragraphs | 29.84 | 23.68 | ↓ -6.17 | **yes** (±6.15) |
| S2 | long sentence then punch | % of paragraphs | 6.87 | 4.85 | ↓ -2.02 | no (±3.99) |
| S3 | That/This pivot opener | % of sentences | 4.86 | 2.65 | ↓ -2.21 | **yes** (±1.77) |
| S4a | headers | per 1k words | 9.00 | 3.95 | ↓ -5.05 | **yes** (±0.87) |
| S4b | table rows | per 1k words | 4.21 | 2.09 | ↓ -2.11 | **yes** (±1.12) |
| S5 | inline bold emphasis | per 1k words | 3.97 | 2.07 | ↓ -1.90 | **yes** (±1.36) |
| S6 | em-dash | per 1k words | 11.96 | 0.55 | ↓ -11.42 | **yes** (±1.25) |
| S7 | terminal service offer | % of samples | 16.67 | 0.00 | ↓ -16.67 | **yes** (±11.11) |
| S8 | arrow as connective | per 1k words | 1.69 | 0.03 | ↓ -1.66 | **yes** (±0.51) |
| S9 | unattached label | per 1k words | 1.43 | 0.00 | ↓ -1.43 | **yes** (±0.48) |
| | **held-out** | | | | | |
| H1 | hedge density | per 1k words | 1.50 | 0.91 | ↓ -0.59 | no (±0.88) |
| H2 | intensifier density | per 1k words | 1.20 | 1.34 | ↑ +0.14 | no (±1.08) |
| H3 | tricolon | per 1k words | 0.54 | 0.83 | ↑ +0.29 | no (±0.39) |
| | **collateral** | | | | | |
| K1 | list items | per 1k words | 10.78 | 4.63 | ↓ -6.14 | **yes** (±2.26) |
| K2 | code blocks | per 1k words | 2.08 | 1.29 | ↓ -0.79 | **yes** (±0.40) |
| K3 | opening paragraph | words | 28.44 | 36.72 | ↑ +8.28 | **yes** (±8.26) |
| K4 | grid tables | per 1k words | 0.60 | 0.27 | ↓ -0.34 | **yes** (±0.21) |
| | **context** | | | | | |
| C1 | output length | words | 641.44 | 540.56 | ↓ -100.89 | **yes** (±45.26) |
| C2 | mean paragraph length | words | 37.57 | 56.65 | ↑ +19.08 | **yes** (±4.98) |
| C3 | mean sentence length | words | 15.64 | 21.10 | ↑ +5.46 | **yes** (±1.06) |


*Band is two pooled standard errors of the difference between the arms' means, built from within-prompt variance only: both arms answer the same 12 frozen prompts, so between-prompt spread cancels in the difference and is not noise. At 12 prompts there is no power for significance testing; this is effect size against measured variance.*


## Blinded pairwise judge

- **judge** `claude-sonnet-5`, minimal system prompt, same clean room
- **substrate** A · **pairing** repeat · **rubric** `d6f49c803cad9f3a`
- **control** 20260903T003018Z
- 72 judgements over 36 pairs, each pair twice with the sides swapped · $1.60

| outcome | pairs | share |
|---|---:|---:|
| treatment preferred | 24 | 66.7% |
| control preferred | 1 | 2.8% |
| tie (the two orders disagreed) | 11 | 30.6% |

Treatment wins **96.0%** of the pairs the judge decided consistently. Swap-disagreement rate **30.56%**; the judge picked whichever text was shown first in **43.06%** of readable judgements, against 50% for an unbiased judge.

| register | treatment | control | tie |
|---|---:|---:|---:|
| conversational | 16 | 0 | 5 |
| document | 8 | 1 | 6 |

The control was preferred on `d01`. A prompt the control wins is where the rules cost something, and is the first place to read rather than to measure.