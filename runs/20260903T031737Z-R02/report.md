# Eval report — 20260903T031737Z-R02

- **arm** treatment · rules `R02`
- **style sha256** `0f7097984b743a29`
- **model** `claude-opus-5[1m]` · **corpus** v1
- **baseline** 20260903T003018Z (control)
- **cost** $6.28 · **failed samples** 0


## Substrate A  (n=36 control → n=36 treatment)

| id | metric | unit | control | this run | delta | cleared band? |
|---|---|---|---:|---:|---:|---|
| | **suppressed** | | | | | |
| S1 | one-sentence paragraphs | % of paragraphs | 29.84 | 7.58 | ↓ -22.27 | **yes** (±5.03) |
| S2 | long sentence then punch | % of paragraphs | 6.87 | 3.25 | ↓ -3.62 | **yes** (±2.95) |
| S3 | That/This pivot opener | % of sentences | 4.86 | 0.93 | ↓ -3.92 | **yes** (±1.46) |
| S4a | headers | per 1k words | 9.00 | 4.47 | ↓ -4.53 | **yes** (±1.03) |
| S4b | table rows | per 1k words | 4.21 | 2.16 | ↓ -2.05 | **yes** (±1.20) |
| S5 | inline bold emphasis | per 1k words | 1.28 | 0.16 | ↓ -1.13 | **yes** (±0.61) |
| S6 | em-dash | per 1k words | 11.96 | 8.44 | ↓ -3.53 | **yes** (±1.51) |
| S7 | terminal service offer | % of samples | 16.67 | 8.33 | ↓ -8.33 | no (±13.61) |
| S8 | arrow as connective | per 1k words | 1.69 | 0.08 | ↓ -1.61 | **yes** (±0.54) |
| S9 | unattached label | per 1k words | 1.43 | 0.00 | ↓ -1.43 | **yes** (±0.48) |
| | **held-out** | | | | | |
| H1 | hedge density | per 1k words | 1.50 | 1.30 | ↓ -0.20 | no (±0.82) |
| H2 | intensifier density | per 1k words | 1.20 | 1.44 | ↑ +0.23 | no (±0.69) |
| H3 | tricolon | per 1k words | 0.54 | 0.55 | ↑ +0.01 | no (±0.46) |
| | **collateral** | | | | | |
| K1 | list items | per 1k words | 10.78 | 1.28 | ↓ -9.49 | **yes** (±1.81) |
| K2 | code blocks | per 1k words | 2.08 | 0.94 | ↓ -1.14 | **yes** (±0.39) |
| K3 | opening paragraph | words | 28.44 | 58.75 | ↑ +30.31 | **yes** (±11.14) |
| K4 | grid tables | per 1k words | 0.60 | 0.24 | ↓ -0.36 | **yes** (±0.20) |
| | **context** | | | | | |
| C1 | output length | words | 641.44 | 637.17 | ↓ -4.28 | no (±49.67) |
| C2 | mean paragraph length | words | 37.57 | 75.27 | ↑ +37.69 | **yes** (±5.62) |
| C3 | mean sentence length | words | 15.64 | 25.88 | ↑ +10.24 | **yes** (±1.25) |

## Substrate B  (n=60 control → n=60 treatment)

| id | metric | unit | control | this run | delta | cleared band? |
|---|---|---|---:|---:|---:|---|
| | **suppressed** | | | | | |
| S1 | one-sentence paragraphs | % of paragraphs | 29.85 | 7.01 | ↓ -22.84 | **yes** (±3.95) |
| S2 | long sentence then punch | % of paragraphs | 6.58 | 4.18 | ↓ -2.40 | no (±3.11) |
| S3 | That/This pivot opener | % of sentences | 3.79 | 1.54 | ↓ -2.25 | **yes** (±1.06) |
| S4a | headers | per 1k words | 10.30 | 5.33 | ↓ -4.97 | **yes** (±0.66) |
| S4b | table rows | per 1k words | 4.20 | 1.77 | ↓ -2.43 | **yes** (±0.92) |
| S5 | inline bold emphasis | per 1k words | 2.00 | 0.26 | ↓ -1.73 | **yes** (±0.66) |
| S6 | em-dash | per 1k words | 10.75 | 7.87 | ↓ -2.88 | **yes** (±1.14) |
| S7 | terminal service offer | % of samples | 23.33 | 5.00 | ↓ -18.33 | **yes** (±10.00) |
| S8 | arrow as connective | per 1k words | 0.91 | 0.00 | ↓ -0.91 | **yes** (±0.33) |
| S9 | unattached label | per 1k words | 0.59 | 0.00 | ↓ -0.59 | **yes** (±0.38) |
| | **held-out** | | | | | |
| H1 | hedge density | per 1k words | 2.04 | 1.46 | ↓ -0.58 | no (±0.70) |
| H2 | intensifier density | per 1k words | 1.87 | 2.22 | ↑ +0.35 | no (±0.66) |
| H3 | tricolon | per 1k words | 0.57 | 0.64 | ↑ +0.07 | no (±0.27) |
| | **collateral** | | | | | |
| K1 | list items | per 1k words | 12.78 | 0.87 | ↓ -11.91 | **yes** (±1.15) |
| K2 | code blocks | per 1k words | 2.23 | 1.09 | ↓ -1.13 | **yes** (±0.49) |
| K3 | opening paragraph | words | 27.92 | 64.73 | ↑ +36.82 | **yes** (±6.74) |
| K4 | grid tables | per 1k words | 0.48 | 0.16 | ↓ -0.32 | **yes** (±0.11) |
| | **context** | | | | | |
| C1 | output length | words | 617.87 | 568.05 | ↓ -49.82 | **yes** (±24.69) |
| C2 | mean paragraph length | words | 36.24 | 78.39 | ↑ +42.14 | **yes** (±4.30) |
| C3 | mean sentence length | words | 15.86 | 26.15 | ↑ +10.30 | **yes** (±1.12) |


*Band is two pooled standard errors of the difference between the arms' means, built from within-prompt variance only: both arms answer the same 12 frozen prompts, so between-prompt spread cancels in the difference and is not noise. At 12 prompts there is no power for significance testing; this is effect size against measured variance.*
