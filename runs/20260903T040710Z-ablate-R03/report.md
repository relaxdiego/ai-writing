# Eval report — 20260903T040710Z-ablate-R03

- **arm** treatment · rules `R02, R04, R05, R06`
- **style sha256** `108ae8328520294c`
- **model** `claude-opus-5[1m]` · **corpus** v1
- **baseline** 20260903T003018Z (control)
- **cost** $6.02 · **failed samples** 0


## Substrate A  (n=36 control → n=36 treatment)

| id | metric | unit | control | this run | delta | cleared band? |
|---|---|---|---:|---:|---:|---|
| | **suppressed** | | | | | |
| S1 | one-sentence paragraphs | % of paragraphs | 29.84 | 4.76 | ↓ -25.08 | **yes** (±4.68) |
| S2 | long sentence then punch | % of paragraphs | 6.87 | 3.75 | ↓ -3.12 | no (±3.68) |
| S3 | That/This pivot opener | % of sentences | 4.86 | 2.47 | ↓ -2.39 | **yes** (±1.79) |
| S4a | headers | per 1k words | 9.00 | 3.44 | ↓ -5.56 | **yes** (±0.84) |
| S4b | table rows | per 1k words | 4.21 | 0.00 | ↓ -4.21 | **yes** (±0.86) |
| S5 | inline bold emphasis | per 1k words | 1.28 | 0.00 | ↓ -1.28 | **yes** (±0.57) |
| S6 | em-dash | per 1k words | 11.96 | 0.59 | ↓ -11.37 | **yes** (±1.28) |
| S7 | terminal service offer | % of samples | 16.67 | 0.00 | ↓ -16.67 | **yes** (±11.11) |
| S8 | arrow as connective | per 1k words | 1.69 | 0.00 | ↓ -1.69 | **yes** (±0.51) |
| S9 | unattached label | per 1k words | 1.43 | 0.00 | ↓ -1.43 | **yes** (±0.48) |
| | **held-out** | | | | | |
| H1 | hedge density | per 1k words | 1.50 | 0.99 | ↓ -0.51 | no (±0.87) |
| H2 | intensifier density | per 1k words | 1.20 | 1.91 | ↑ +0.71 | no (±1.15) |
| H3 | tricolon | per 1k words | 0.54 | 0.76 | ↑ +0.22 | no (±0.42) |
| | **collateral** | | | | | |
| K1 | list items | per 1k words | 10.78 | 0.80 | ↓ -9.98 | **yes** (±1.89) |
| K2 | code blocks | per 1k words | 2.08 | 0.82 | ↓ -1.27 | **yes** (±0.38) |
| K3 | opening paragraph | words | 28.44 | 66.64 | ↑ +38.19 | **yes** (±9.74) |
| K4 | grid tables | per 1k words | 0.60 | 0.00 | ↓ -0.60 | **yes** (±0.17) |
| | **context** | | | | | |
| C1 | output length | words | 641.44 | 533.17 | ↓ -108.28 | **yes** (±47.47) |
| C2 | mean paragraph length | words | 37.57 | 82.02 | ↑ +44.44 | **yes** (±5.45) |
| C3 | mean sentence length | words | 15.64 | 24.71 | ↑ +9.07 | **yes** (±1.04) |

## Substrate B  (n=60 control → n=60 treatment)

| id | metric | unit | control | this run | delta | cleared band? |
|---|---|---|---:|---:|---:|---|
| | **suppressed** | | | | | |
| S1 | one-sentence paragraphs | % of paragraphs | 29.85 | 6.93 | ↓ -22.92 | **yes** (±3.95) |
| S2 | long sentence then punch | % of paragraphs | 6.58 | 4.70 | ↓ -1.88 | no (±2.84) |
| S3 | That/This pivot opener | % of sentences | 3.79 | 2.76 | ↓ -1.03 | no (±1.18) |
| S4a | headers | per 1k words | 10.30 | 3.89 | ↓ -6.42 | **yes** (±0.59) |
| S4b | table rows | per 1k words | 4.20 | 0.00 | ↓ -4.20 | **yes** (±0.87) |
| S5 | inline bold emphasis | per 1k words | 2.00 | 0.00 | ↓ -2.00 | **yes** (±0.62) |
| S6 | em-dash | per 1k words | 10.75 | 1.45 | ↓ -9.30 | **yes** (±1.06) |
| S7 | terminal service offer | % of samples | 23.33 | 0.00 | ↓ -23.33 | **yes** (±9.13) |
| S8 | arrow as connective | per 1k words | 0.91 | 0.00 | ↓ -0.91 | **yes** (±0.33) |
| S9 | unattached label | per 1k words | 0.59 | 0.00 | ↓ -0.59 | **yes** (±0.38) |
| | **held-out** | | | | | |
| H1 | hedge density | per 1k words | 2.04 | 1.33 | ↓ -0.71 | **yes** (±0.68) |
| H2 | intensifier density | per 1k words | 1.87 | 1.40 | ↓ -0.48 | no (±0.62) |
| H3 | tricolon | per 1k words | 0.57 | 0.88 | ↑ +0.31 | **yes** (±0.30) |
| | **collateral** | | | | | |
| K1 | list items | per 1k words | 12.78 | 1.07 | ↓ -11.71 | **yes** (±1.01) |
| K2 | code blocks | per 1k words | 2.23 | 1.01 | ↓ -1.21 | **yes** (±0.38) |
| K3 | opening paragraph | words | 27.92 | 67.98 | ↑ +40.07 | **yes** (±9.68) |
| K4 | grid tables | per 1k words | 0.48 | 0.00 | ↓ -0.48 | **yes** (±0.10) |
| | **context** | | | | | |
| C1 | output length | words | 617.87 | 529.87 | ↓ -88.00 | **yes** (±25.40) |
| C2 | mean paragraph length | words | 36.24 | 82.28 | ↑ +46.03 | **yes** (±4.22) |
| C3 | mean sentence length | words | 15.86 | 25.03 | ↑ +9.17 | **yes** (±0.96) |


*Band is two pooled standard errors of the difference between the arms' means, built from within-prompt variance only: both arms answer the same 12 frozen prompts, so between-prompt spread cancels in the difference and is not noise. At 12 prompts there is no power for significance testing; this is effect size against measured variance.*


## Blinded pairwise judge

- **judge** `claude-sonnet-5`, minimal system prompt, same clean room
- **substrate** A · **pairing** repeat · **rubric** `d6f49c803cad9f3a`
- **control** 20260903T003018Z
- 72 judgements over 36 pairs, each pair twice with the sides swapped · $1.48

| outcome | pairs | share |
|---|---:|---:|
| treatment preferred | 24 | 66.7% |
| control preferred | 3 | 8.3% |
| tie (the two orders disagreed) | 9 | 25.0% |

Treatment wins **88.89%** of the pairs the judge decided consistently. Swap-disagreement rate **25.0%**; the judge picked whichever text was shown first in **45.83%** of readable judgements, against 50% for an unbiased judge.

| register | treatment | control | tie |
|---|---:|---:|---:|
| conversational | 15 | 1 | 5 |
| document | 9 | 2 | 4 |

The control was preferred on `c06`, `d01`. A prompt the control wins is where the rules cost something, and is the first place to read rather than to measure.