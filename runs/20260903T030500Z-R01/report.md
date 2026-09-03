# Eval report — 20260903T030500Z-R01

- **arm** treatment · rules `R01`
- **style sha256** `c0b903f43d8e634a`
- **model** `claude-opus-5[1m]` · **corpus** v1
- **baseline** 20260903T003018Z (control)
- **cost** $4.24 · **failed samples** 0


## Substrate A  (n=36 control → n=36 treatment)

| id | metric | unit | control | this run | delta | cleared band? |
|---|---|---|---:|---:|---:|---|
| | **suppressed** | | | | | |
| S1 | one-sentence paragraphs | % of paragraphs | 31.54 | 23.90 | ↓ -7.64 | **yes** (±6.44) |
| S2 | long sentence then punch | % of paragraphs | 9.38 | 8.14 | ↓ -1.24 | no (±8.74) |
| S3 | That/This pivot opener | % of sentences | 4.80 | 3.81 | ↓ -0.99 | no (±2.29) |
| S4a | headers | per 1k words | 9.00 | 6.91 | ↓ -2.09 | **yes** (±1.31) |
| S4b | table rows | per 1k words | 4.21 | 2.27 | ↓ -1.94 | **yes** (±1.33) |
| S5 | inline bold emphasis | per 1k words | 3.97 | 2.19 | ↓ -1.78 | **yes** (±1.66) |
| S6 | em-dash | per 1k words | 11.96 | 10.50 | ↓ -1.46 | no (±1.60) |
| S7 | terminal service offer | % of samples | 16.67 | 13.89 | ↓ -2.78 | no (±13.61) |
| | **held-out** | | | | | |
| H1 | hedge density | per 1k words | 1.50 | 0.74 | ↓ -0.76 | **yes** (±0.75) |
| H2 | intensifier density | per 1k words | 1.20 | 0.97 | ↓ -0.23 | no (±0.51) |
| H3 | tricolon | per 1k words | 0.54 | 0.54 | ↑ +0.01 | no (±0.40) |
| | **collateral** | | | | | |
| K1 | list items | per 1k words | 10.78 | 7.61 | ↓ -3.16 | **yes** (±3.12) |
| K2 | code blocks | per 1k words | 2.08 | 2.05 | ↓ -0.03 | no (±0.62) |
| K3 | opening paragraph | words | 28.44 | 27.39 | ↓ -1.05 | no (±4.89) |
| K4 | grid tables | per 1k words | 0.60 | 0.19 | ↓ -0.42 | **yes** (±0.20) |
| | **context** | | | | | |
| C1 | output length | words | 641.44 | 414.75 | ↓ -226.69 | **yes** (±43.10) |
| C2 | mean paragraph length | words | 36.87 | 38.25 | ↑ +1.38 | no (±4.94) |
| C3 | mean sentence length | words | 15.48 | 15.22 | ↓ -0.25 | no (±1.05) |

## Substrate B  (n=60 control → n=60 treatment)

| id | metric | unit | control | this run | delta | cleared band? |
|---|---|---|---:|---:|---:|---|
| | **suppressed** | | | | | |
| S1 | one-sentence paragraphs | % of paragraphs | 31.56 | 27.79 | ↓ -3.77 | no (±4.96) |
| S2 | long sentence then punch | % of paragraphs | 8.06 | 8.05 | ↓ -0.02 | no (±4.01) |
| S3 | That/This pivot opener | % of sentences | 3.76 | 3.11 | ↓ -0.65 | no (±1.44) |
| S4a | headers | per 1k words | 10.30 | 9.07 | ↓ -1.23 | **yes** (±0.99) |
| S4b | table rows | per 1k words | 4.20 | 2.14 | ↓ -2.06 | **yes** (±0.98) |
| S5 | inline bold emphasis | per 1k words | 6.81 | 3.67 | ↓ -3.14 | **yes** (±1.46) |
| S6 | em-dash | per 1k words | 10.75 | 9.08 | ↓ -1.67 | **yes** (±1.29) |
| S7 | terminal service offer | % of samples | 23.33 | 6.67 | ↓ -16.67 | **yes** (±10.54) |
| | **held-out** | | | | | |
| H1 | hedge density | per 1k words | 2.04 | 2.27 | ↑ +0.23 | no (±0.86) |
| H2 | intensifier density | per 1k words | 1.87 | 1.62 | ↓ -0.26 | no (±0.72) |
| H3 | tricolon | per 1k words | 0.57 | 0.54 | ↓ -0.02 | no (±0.25) |
| | **collateral** | | | | | |
| K1 | list items | per 1k words | 12.78 | 8.85 | ↓ -3.94 | **yes** (±1.53) |
| K2 | code blocks | per 1k words | 2.23 | 2.77 | ↑ +0.55 | **yes** (±0.49) |
| K3 | opening paragraph | words | 27.92 | 22.25 | ↓ -5.67 | **yes** (±4.21) |
| K4 | grid tables | per 1k words | 0.48 | 0.17 | ↓ -0.31 | **yes** (±0.10) |
| | **context** | | | | | |
| C1 | output length | words | 617.87 | 374.95 | ↓ -242.92 | **yes** (±21.31) |
| C2 | mean paragraph length | words | 35.47 | 36.79 | ↑ +1.32 | no (±2.96) |
| C3 | mean sentence length | words | 15.64 | 16.11 | ↑ +0.48 | no (±0.98) |


*Band is two pooled standard errors of the difference between the arms' means, built from within-prompt variance only: both arms answer the same 12 frozen prompts, so between-prompt spread cancels in the difference and is not noise. At 12 prompts there is no power for significance testing; this is effect size against measured variance.*
