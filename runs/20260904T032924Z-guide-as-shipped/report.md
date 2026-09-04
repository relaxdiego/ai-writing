# Eval report — 20260904T032924Z-guide-as-shipped

- **arm** treatment · rules `R07, R08, R09, R10, R05, R06`
- **style sha256** `f20b1ebd89e14ddd`
- **model** `claude-opus-5[1m]` · **corpus** v2
- **baseline** 20260903T202317Z-v2-control (control)
- **cost** $2.93 · **failed samples** 0


## Substrate A  (n=36 control → n=36 treatment)

| id | metric | unit | control | this run | delta | cleared band? |
|---|---|---|---:|---:|---:|---|
| | **suppressed** | | | | | |
| S1 | one-sentence paragraphs | % of paragraphs | 34.10 | 13.43 | ↓ -20.67 | **yes** (±6.45) |
| S2 | long sentence then punch | % of paragraphs | 7.26 | 4.95 | ↓ -2.31 | no (±3.60) |
| S3 | That/This pivot opener | % of sentences | 4.36 | 2.18 | ↓ -2.19 | **yes** (±1.68) |
| S4a | headers | per 1k words | 7.39 | 4.94 | ↓ -2.45 | **yes** (±0.72) |
| S4b | table rows | per 1k words | 4.60 | 4.18 | ↓ -0.42 | no (±1.79) |
| S5 | inline bold emphasis | per 1k words | 0.64 | 0.13 | ↓ -0.51 | **yes** (±0.36) |
| S6 | em-dash | per 1k words | 12.01 | 2.78 | ↓ -9.23 | **yes** (±1.25) |
| S7 | terminal service offer | % of samples | 22.22 | 0.00 | ↓ -22.22 | **yes** (±13.61) |
| S8 | arrow as connective | per 1k words | 0.85 | 0.00 | ↓ -0.85 | **yes** (±0.36) |
| S9 | unattached label | per 1k words | 0.52 | 0.00 | ↓ -0.52 | no (±0.86) |
| | **held-out** | | | | | |
| H1 | hedge density | per 1k words | 1.04 | 0.71 | ↓ -0.34 | no (±0.54) |
| H2 | intensifier density | per 1k words | 1.24 | 1.19 | ↓ -0.05 | no (±0.51) |
| H3 | tricolon | per 1k words | 0.56 | 0.40 | ↓ -0.16 | no (±0.53) |
| | **collateral** | | | | | |
| K1 | list items | per 1k words | 10.06 | 4.34 | ↓ -5.72 | **yes** (±1.88) |
| K2 | code blocks | per 1k words | 3.47 | 2.01 | ↓ -1.46 | **yes** (±0.73) |
| K3 | opening paragraph | words | 27.72 | 38.39 | ↑ +10.67 | **yes** (±8.75) |
| K4 | grid tables | per 1k words | 0.55 | 0.64 | ↑ +0.10 | no (±0.33) |
| | **context** | | | | | |
| C1 | output length | words | 574.33 | 553.89 | ↓ -20.44 | no (±49.78) |
| C2 | mean paragraph length | words | 31.33 | 55.42 | ↑ +24.09 | **yes** (±3.19) |
| C3 | mean sentence length | words | 15.90 | 21.31 | ↑ +5.41 | **yes** (±1.01) |


*Band is two pooled standard errors of the difference between the arms' means, built from within-prompt variance only: both arms answer the same 12 frozen prompts, so between-prompt spread cancels in the difference and is not noise. At 12 prompts there is no power for significance testing; this is effect size against measured variance.*
