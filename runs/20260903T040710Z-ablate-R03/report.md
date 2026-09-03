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
| S1 | one-sentence paragraphs | % of paragraphs | 31.54 | 6.79 | ↓ -24.75 | **yes** (±9.23) |
| S2 | long sentence then punch | % of paragraphs | 9.38 | 3.09 | ↓ -6.29 | **yes** (±6.23) |
| S3 | That/This pivot opener | % of sentences | 4.80 | 2.32 | ↓ -2.48 | **yes** (±2.02) |
| S4a | headers | per 1k words | 9.00 | 3.44 | ↓ -5.56 | **yes** (±2.50) |
| S4b | table rows | per 1k words | 4.21 | 0.00 | ↓ -4.21 | **yes** (±2.17) |
| S5 | inline bold emphasis | per 1k words | 3.97 | 0.27 | ↓ -3.70 | **yes** (±1.39) |
| S6 | em-dash | per 1k words | 11.96 | 0.59 | ↓ -11.37 | **yes** (±2.06) |
| S7 | terminal service offer | % of samples | 16.67 | 0.00 | ↓ -16.67 | **yes** (±12.60) |
| | **held-out** | | | | | |
| H1 | hedge density | per 1k words | 1.50 | 0.99 | ↓ -0.51 | no (±0.93) |
| H2 | intensifier density | per 1k words | 1.20 | 1.91 | ↑ +0.71 | no (±1.22) |
| H3 | tricolon | per 1k words | 0.54 | 0.76 | ↑ +0.22 | no (±0.61) |
| | **collateral** | | | | | |
| K1 | list items | per 1k words | 10.78 | 0.80 | ↓ -9.98 | **yes** (±3.20) |
| K2 | code blocks | per 1k words | 2.08 | 0.86 | ↓ -1.23 | no (±1.35) |
| K3 | opening paragraph | words | 28.44 | 64.86 | ↑ +36.42 | **yes** (±15.60) |
| | **context** | | | | | |
| C1 | output length | words | 641.44 | 533.22 | ↓ -108.22 | no (±160.25) |
| C2 | mean paragraph length | words | 36.87 | 81.20 | ↑ +44.33 | **yes** (±11.53) |
| C3 | mean sentence length | words | 15.48 | 24.59 | ↑ +9.11 | **yes** (±1.67) |

## Substrate B  (n=60 control → n=60 treatment)

| id | metric | unit | control | this run | delta | cleared band? |
|---|---|---|---:|---:|---:|---|
| | **suppressed** | | | | | |
| S1 | one-sentence paragraphs | % of paragraphs | 31.56 | 8.04 | ↓ -23.52 | **yes** (±6.91) |
| S2 | long sentence then punch | % of paragraphs | 8.06 | 3.23 | ↓ -4.83 | **yes** (±3.67) |
| S3 | That/This pivot opener | % of sentences | 3.76 | 2.76 | ↓ -1.00 | no (±1.56) |
| S4a | headers | per 1k words | 10.30 | 3.88 | ↓ -6.42 | **yes** (±2.21) |
| S4b | table rows | per 1k words | 4.20 | 0.00 | ↓ -4.20 | **yes** (±1.88) |
| S5 | inline bold emphasis | per 1k words | 6.81 | 0.80 | ↓ -6.01 | **yes** (±1.50) |
| S6 | em-dash | per 1k words | 10.75 | 1.45 | ↓ -9.30 | **yes** (±1.52) |
| S7 | terminal service offer | % of samples | 23.33 | 0.00 | ↓ -23.33 | **yes** (±11.01) |
| | **held-out** | | | | | |
| H1 | hedge density | per 1k words | 2.04 | 1.33 | ↓ -0.71 | no (±0.92) |
| H2 | intensifier density | per 1k words | 1.87 | 1.40 | ↓ -0.48 | no (±0.73) |
| H3 | tricolon | per 1k words | 0.57 | 0.88 | ↑ +0.31 | no (±0.49) |
| | **collateral** | | | | | |
| K1 | list items | per 1k words | 12.78 | 1.07 | ↓ -11.71 | **yes** (±2.31) |
| K2 | code blocks | per 1k words | 2.23 | 1.03 | ↓ -1.19 | no (±1.23) |
| K3 | opening paragraph | words | 27.92 | 67.10 | ↑ +39.18 | **yes** (±13.41) |
| | **context** | | | | | |
| C1 | output length | words | 617.87 | 529.90 | ↓ -87.97 | no (±105.56) |
| C2 | mean paragraph length | words | 35.47 | 81.84 | ↑ +46.38 | **yes** (±9.13) |
| C3 | mean sentence length | words | 15.64 | 24.96 | ↑ +9.32 | **yes** (±1.30) |


*Band is two pooled standard errors of the difference between the arms' means. At 12 prompts there is no power for significance testing; this is effect size against measured variance.*


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