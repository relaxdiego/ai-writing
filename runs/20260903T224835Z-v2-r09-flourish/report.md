# Eval report — 20260903T224835Z-v2-r09-flourish

- **arm** treatment · rules `R07, R08, R09, R04, R05, R06`
- **style sha256** `bb3535a154df58ae`
- **model** `claude-opus-5[1m]` · **corpus** v2
- **baseline** 20260903T202854Z-v2-treatment (treatment)
- **cost** $2.81 · **failed samples** 0


## Substrate A  (n=36 control → n=36 treatment)

| id | metric | unit | control | this run | delta | cleared band? |
|---|---|---|---:|---:|---:|---|
| | **suppressed** | | | | | |
| S1 | one-sentence paragraphs | % of paragraphs | 20.41 | 17.02 | ↓ -3.39 | no (±6.24) |
| S2 | long sentence then punch | % of paragraphs | 3.75 | 3.50 | ↓ -0.25 | no (±3.47) |
| S3 | That/This pivot opener | % of sentences | 3.28 | 2.30 | ↓ -0.98 | no (±1.80) |
| S4a | headers | per 1k words | 3.60 | 3.31 | ↓ -0.30 | no (±0.41) |
| S4b | table rows | per 1k words | 1.36 | 1.15 | ↓ -0.21 | no (±1.23) |
| S5 | inline bold emphasis | per 1k words | 0.00 | 0.09 | ↑ +0.09 | no (±0.09) |
| S6 | em-dash | per 1k words | 0.75 | 0.15 | ↓ -0.59 | no (±0.97) |
| S7 | terminal service offer | % of samples | 0.00 | 0.00 | · +0.00 | no (±0.00) |
| S8 | arrow as connective | per 1k words | 0.07 | 0.07 | ↓ -0.00 | no (±0.20) |
| S9 | unattached label | per 1k words | 0.00 | 0.00 | · +0.00 | no (±0.00) |
| | **held-out** | | | | | |
| H1 | hedge density | per 1k words | 1.45 | 1.13 | ↓ -0.33 | no (±0.56) |
| H2 | intensifier density | per 1k words | 1.50 | 0.88 | ↓ -0.62 | **yes** (±0.57) |
| H3 | tricolon | per 1k words | 0.72 | 0.86 | ↑ +0.14 | no (±0.59) |
| | **collateral** | | | | | |
| K1 | list items | per 1k words | 5.94 | 4.88 | ↓ -1.06 | no (±1.74) |
| K2 | code blocks | per 1k words | 1.55 | 2.10 | ↑ +0.55 | no (±0.62) |
| K3 | opening paragraph | words | 37.50 | 29.36 | ↓ -8.14 | **yes** (±6.86) |
| K4 | grid tables | per 1k words | 0.18 | 0.12 | ↓ -0.06 | no (±0.18) |
| K5 | em-dash interruption | per 1k words | 0.08 | 0.00 | ↓ -0.08 | no (±0.15) |
| | **context** | | | | | |
| C1 | output length | words | 475.19 | 482.39 | ↑ +7.19 | no (±34.63) |
| C2 | mean paragraph length | words | 54.88 | 53.82 | ↓ -1.06 | no (±5.14) |
| C3 | mean sentence length | words | 21.43 | 21.30 | ↓ -0.13 | no (±1.06) |


*Band is two pooled standard errors of the difference between the arms' means, built from within-prompt variance only: both arms answer the same 12 frozen prompts, so between-prompt spread cancels in the difference and is not noise. At 12 prompts there is no power for significance testing; this is effect size against measured variance.*
