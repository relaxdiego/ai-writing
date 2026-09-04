# Eval report — 20260904T051132Z-R06-no-permit

- **arm** treatment · rules `R07, R08, R09, R10, R05, R06`
- **style sha256** `e139dce090b96d65`
- **model** `claude-opus-5[1m]` · **corpus** v2
- **baseline** 20260903T231128Z-R10-scan-not-length (treatment)
- **cost** $2.75 · **failed samples** 0


## Substrate A  (n=36 control → n=36 treatment)

| id | metric | unit | control | this run | delta | cleared band? |
|---|---|---|---:|---:|---:|---|
| | **suppressed** | | | | | |
| S1 | one-sentence paragraphs | % of paragraphs | 18.82 | 15.64 | ↓ -3.19 | no (±5.02) |
| S2 | long sentence then punch | % of paragraphs | 6.91 | 6.25 | ↓ -0.66 | no (±4.67) |
| S3 | That/This pivot opener | % of sentences | 3.65 | 4.04 | ↑ +0.39 | no (±2.04) |
| S4a | headers | per 1k words | 4.35 | 4.41 | ↑ +0.06 | no (±0.43) |
| S4b | table rows | per 1k words | 5.64 | 6.48 | ↑ +0.84 | no (±2.19) |
| S5 | inline bold emphasis | per 1k words | 0.03 | 0.03 | ↑ +0.00 | no (±0.09) |
| S6 | em-dash | per 1k words | 0.04 | 1.72 | ↑ +1.68 | **yes** (±0.98) |
| S7 | terminal service offer | % of samples | 0.00 | 5.56 | ↑ +5.56 | no (±5.56) |
| S8 | arrow as connective | per 1k words | 0.21 | 0.20 | ↓ -0.01 | no (±0.04) |
| S9 | unattached label | per 1k words | 0.00 | 0.00 | · +0.00 | no (±0.00) |
| | **held-out** | | | | | |
| H1 | hedge density | per 1k words | 0.99 | 1.42 | ↑ +0.43 | no (±0.50) |
| H2 | intensifier density | per 1k words | 1.14 | 1.16 | ↑ +0.01 | no (±0.45) |
| H3 | tricolon | per 1k words | 0.88 | 0.96 | ↑ +0.08 | no (±0.58) |
| | **collateral** | | | | | |
| K1 | list items | per 1k words | 3.52 | 2.83 | ↓ -0.70 | no (±1.80) |
| K2 | code blocks | per 1k words | 1.90 | 1.81 | ↓ -0.09 | no (±0.54) |
| K3 | opening paragraph | words | 39.75 | 34.08 | ↓ -5.67 | no (±8.28) |
| K4 | grid tables | per 1k words | 0.78 | 0.96 | ↑ +0.17 | no (±0.35) |
| K5 | em-dash interruption | per 1k words | 0.00 | 0.90 | ↑ +0.90 | no (±0.91) |
| | **context** | | | | | |
| C1 | output length | words | 547.78 | 562.78 | ↑ +15.00 | no (±48.67) |
| C2 | mean paragraph length | words | 56.47 | 53.68 | ↓ -2.79 | no (±4.51) |
| C3 | mean sentence length | words | 21.85 | 20.92 | ↓ -0.94 | no (±0.95) |


*Band is two pooled standard errors of the difference between the arms' means, built from within-prompt variance only: both arms answer the same 12 frozen prompts, so between-prompt spread cancels in the difference and is not noise. At 12 prompts there is no power for significance testing; this is effect size against measured variance.*
