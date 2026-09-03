# Eval report — 20260903T035059Z-R03-R06

- **arm** treatment · rules `R02, R03, R04, R05, R06`
- **style sha256** `7695fb2eade6790e`
- **model** `claude-opus-5[1m]` · **corpus** v1
- **baseline** 20260903T003018Z (control)
- **cost** $6.56 · **failed samples** 0


## Substrate A  (n=36 control → n=36 treatment)

| id | metric | unit | control | this run | delta | cleared band? |
|---|---|---|---:|---:|---:|---|
| | **suppressed** | | | | | |
| S1 | one-sentence paragraphs | % of paragraphs | 31.54 | 7.98 | ↓ -23.56 | **yes** (±4.71) |
| S2 | long sentence then punch | % of paragraphs | 6.62 | 3.90 | ↓ -2.73 | no (±3.19) |
| S3 | That/This pivot opener | % of sentences | 4.80 | 2.18 | ↓ -2.62 | **yes** (±1.66) |
| S4a | headers | per 1k words | 9.00 | 4.00 | ↓ -5.00 | **yes** (±0.82) |
| S4b | table rows | per 1k words | 4.21 | 0.00 | ↓ -4.21 | **yes** (±0.86) |
| S5 | inline bold emphasis | per 1k words | 3.97 | 0.55 | ↓ -3.42 | **yes** (±1.39) |
| S6 | em-dash | per 1k words | 11.96 | 0.97 | ↓ -10.99 | **yes** (±1.18) |
| S7 | terminal service offer | % of samples | 16.67 | 0.00 | ↓ -16.67 | **yes** (±11.11) |
| | **held-out** | | | | | |
| H1 | hedge density | per 1k words | 1.50 | 0.87 | ↓ -0.63 | no (±0.70) |
| H2 | intensifier density | per 1k words | 1.20 | 1.05 | ↓ -0.15 | no (±0.60) |
| H3 | tricolon | per 1k words | 0.54 | 0.78 | ↑ +0.25 | no (±0.37) |
| | **collateral** | | | | | |
| K1 | list items | per 1k words | 10.78 | 1.33 | ↓ -9.44 | **yes** (±1.66) |
| K2 | code blocks | per 1k words | 2.08 | 1.16 | ↓ -0.92 | **yes** (±0.43) |
| K3 | opening paragraph | words | 28.44 | 71.64 | ↑ +43.19 | **yes** (±9.77) |
| K4 | grid tables | per 1k words | 0.60 | 0.00 | ↓ -0.60 | **yes** (±0.17) |
| | **context** | | | | | |
| C1 | output length | words | 641.44 | 534.28 | ↓ -107.17 | **yes** (±45.58) |
| C2 | mean paragraph length | words | 36.87 | 78.75 | ↑ +41.88 | **yes** (±5.92) |
| C3 | mean sentence length | words | 15.48 | 23.73 | ↑ +8.25 | **yes** (±1.12) |

## Substrate B  (n=60 control → n=60 treatment)

| id | metric | unit | control | this run | delta | cleared band? |
|---|---|---|---:|---:|---:|---|
| | **suppressed** | | | | | |
| S1 | one-sentence paragraphs | % of paragraphs | 31.56 | 8.15 | ↓ -23.41 | **yes** (±4.46) |
| S2 | long sentence then punch | % of paragraphs | 6.33 | 3.44 | ↓ -2.89 | **yes** (±2.84) |
| S3 | That/This pivot opener | % of sentences | 3.76 | 2.35 | ↓ -1.41 | **yes** (±1.12) |
| S4a | headers | per 1k words | 10.30 | 3.58 | ↓ -6.72 | **yes** (±0.63) |
| S4b | table rows | per 1k words | 4.20 | 0.00 | ↓ -4.20 | **yes** (±0.87) |
| S5 | inline bold emphasis | per 1k words | 6.81 | 0.60 | ↓ -6.21 | **yes** (±1.24) |
| S6 | em-dash | per 1k words | 10.75 | 1.60 | ↓ -9.14 | **yes** (±0.97) |
| S7 | terminal service offer | % of samples | 23.33 | 0.00 | ↓ -23.33 | **yes** (±9.13) |
| | **held-out** | | | | | |
| H1 | hedge density | per 1k words | 2.04 | 1.32 | ↓ -0.72 | **yes** (±0.69) |
| H2 | intensifier density | per 1k words | 1.87 | 1.00 | ↓ -0.87 | **yes** (±0.54) |
| H3 | tricolon | per 1k words | 0.57 | 0.71 | ↑ +0.14 | no (±0.23) |
| | **collateral** | | | | | |
| K1 | list items | per 1k words | 12.78 | 1.10 | ↓ -11.69 | **yes** (±1.00) |
| K2 | code blocks | per 1k words | 2.23 | 1.03 | ↓ -1.19 | **yes** (±0.38) |
| K3 | opening paragraph | words | 27.92 | 70.15 | ↑ +42.23 | **yes** (±6.45) |
| K4 | grid tables | per 1k words | 0.48 | 0.00 | ↓ -0.48 | **yes** (±0.10) |
| | **context** | | | | | |
| C1 | output length | words | 617.87 | 526.05 | ↓ -91.82 | **yes** (±26.64) |
| C2 | mean paragraph length | words | 35.47 | 79.21 | ↑ +43.74 | **yes** (±3.97) |
| C3 | mean sentence length | words | 15.64 | 24.54 | ↑ +8.90 | **yes** (±0.88) |


*Band is two pooled standard errors of the difference between the arms' means, built from within-prompt variance only: both arms answer the same 12 frozen prompts, so between-prompt spread cancels in the difference and is not noise. At 12 prompts there is no power for significance testing; this is effect size against measured variance.*
