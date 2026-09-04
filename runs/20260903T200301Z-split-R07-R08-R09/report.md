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
| S3 | That/This pivot opener | % of sentences | 4.86 | 2.92 | ↓ -1.94 | **yes** (±1.92) |
| S4a | headers | per 1k words | 9.00 | 3.75 | ↓ -5.25 | **yes** (±1.08) |
| S4b | table rows | per 1k words | 4.21 | 2.24 | ↓ -1.97 | **yes** (±1.14) |
| S5 | inline bold emphasis | per 1k words | 1.28 | 0.00 | ↓ -1.28 | **yes** (±0.57) |
| S6 | em-dash | per 1k words | 9.69 | 0.15 | ↓ -9.54 | **yes** (±1.02) |
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
| K5 | em-dash interruption | per 1k words | 2.25 | 0.00 | ↓ -2.25 | **yes** (±0.94) |
| | **context** | | | | | |
| C1 | output length | words | 641.44 | 534.89 | ↓ -106.55 | **yes** (±46.57) |
| C2 | mean paragraph length | words | 37.57 | 59.62 | ↑ +22.05 | **yes** (±5.29) |
| C3 | mean sentence length | words | 15.64 | 21.28 | ↑ +5.64 | **yes** (±1.22) |


*Band is two pooled standard errors of the difference between the arms' means, built from within-prompt variance only: both arms answer the same 12 frozen prompts, so between-prompt spread cancels in the difference and is not noise. At 12 prompts there is no power for significance testing; this is effect size against measured variance.*
