# Eval report — 20260903T202854Z-v2-treatment

- **arm** treatment · rules `R07, R08, R09, R04, R05, R06`
- **style sha256** `2b62946eda361a23`
- **model** `claude-opus-5[1m]` · **corpus** v2
- **baseline** 20260903T202317Z-v2-control (control)
- **cost** $2.60 · **failed samples** 0


## Substrate A  (n=36 control → n=36 treatment)

| id | metric | unit | control | this run | delta | cleared band? |
|---|---|---|---:|---:|---:|---|
| | **suppressed** | | | | | |
| S1 | one-sentence paragraphs | % of paragraphs | 34.10 | 20.41 | ↓ -13.69 | **yes** (±6.65) |
| S2 | long sentence then punch | % of paragraphs | 7.26 | 3.75 | ↓ -3.51 | no (±3.75) |
| S3 | That/This pivot opener | % of sentences | 4.36 | 3.28 | ↓ -1.08 | no (±2.12) |
| S4a | headers | per 1k words | 7.39 | 3.60 | ↓ -3.79 | **yes** (±0.68) |
| S4b | table rows | per 1k words | 4.60 | 1.36 | ↓ -3.25 | **yes** (±1.52) |
| S5 | inline bold emphasis | per 1k words | 0.64 | 0.00 | ↓ -0.64 | **yes** (±0.25) |
| S6 | em-dash | per 1k words | 12.01 | 0.82 | ↓ -11.19 | **yes** (±1.43) |
| S7 | terminal service offer | % of samples | 22.22 | 0.00 | ↓ -22.22 | **yes** (±13.61) |
| S8 | arrow as connective | per 1k words | 0.85 | 0.07 | ↓ -0.78 | **yes** (±0.38) |
| S9 | unattached label | per 1k words | 0.52 | 0.00 | ↓ -0.52 | no (±0.86) |
| | **held-out** | | | | | |
| H1 | hedge density | per 1k words | 1.04 | 1.45 | ↑ +0.41 | no (±0.53) |
| H2 | intensifier density | per 1k words | 1.24 | 1.50 | ↑ +0.26 | no (±0.60) |
| H3 | tricolon | per 1k words | 0.56 | 0.72 | ↑ +0.16 | no (±0.62) |
| | **collateral** | | | | | |
| K1 | list items | per 1k words | 10.06 | 5.94 | ↓ -4.12 | **yes** (±2.18) |
| K2 | code blocks | per 1k words | 3.47 | 1.55 | ↓ -1.92 | **yes** (±0.67) |
| K3 | opening paragraph | words | 27.72 | 37.50 | ↑ +9.78 | **yes** (±7.64) |
| K4 | grid tables | per 1k words | 0.55 | 0.18 | ↓ -0.36 | **yes** (±0.29) |
| | **context** | | | | | |
| C1 | output length | words | 574.33 | 475.19 | ↓ -99.14 | **yes** (±41.07) |
| C2 | mean paragraph length | words | 31.33 | 54.88 | ↑ +23.56 | **yes** (±3.60) |
| C3 | mean sentence length | words | 15.90 | 21.43 | ↑ +5.53 | **yes** (±0.96) |


*Band is two pooled standard errors of the difference between the arms' means, built from within-prompt variance only: both arms answer the same 12 frozen prompts, so between-prompt spread cancels in the difference and is not noise. At 12 prompts there is no power for significance testing; this is effect size against measured variance.*
