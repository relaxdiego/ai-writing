# Eval report — 20260903T231128Z-R10-scan-not-length

- **arm** treatment · rules `R07, R08, R09, R10, R05, R06`
- **style sha256** `daee39bfb446f72e`
- **model** `claude-opus-5[1m]` · **corpus** v2
- **baseline** 20260903T202317Z-v2-control (control)
- **cost** $2.99 · **failed samples** 0


## Substrate A  (n=36 control → n=36 treatment)

| id | metric | unit | control | this run | delta | cleared band? |
|---|---|---|---:|---:|---:|---|
| | **suppressed** | | | | | |
| S1 | one-sentence paragraphs | % of paragraphs | 34.10 | 18.82 | ↓ -15.28 | **yes** (±6.41) |
| S2 | long sentence then punch | % of paragraphs | 7.26 | 6.91 | ↓ -0.35 | no (±3.83) |
| S3 | That/This pivot opener | % of sentences | 4.36 | 3.69 | ↓ -0.67 | no (±1.98) |
| S4a | headers | per 1k words | 7.39 | 4.35 | ↓ -3.04 | **yes** (±0.73) |
| S4b | table rows | per 1k words | 4.60 | 5.64 | ↑ +1.04 | no (±1.88) |
| S5 | inline bold emphasis | per 1k words | 5.55 | 0.82 | ↓ -4.74 | **yes** (±1.45) |
| S6 | em-dash | per 1k words | 12.01 | 0.04 | ↓ -11.97 | **yes** (±1.04) |
| S7 | terminal service offer | % of samples | 22.22 | 0.00 | ↓ -22.22 | **yes** (±13.61) |
| S8 | arrow as connective | per 1k words | 0.85 | 0.21 | ↓ -0.65 | **yes** (±0.36) |
| S9 | unattached label | per 1k words | 0.52 | 0.00 | ↓ -0.52 | no (±0.86) |
| | **held-out** | | | | | |
| H1 | hedge density | per 1k words | 1.04 | 0.99 | ↓ -0.06 | no (±0.43) |
| H2 | intensifier density | per 1k words | 1.24 | 1.14 | ↓ -0.09 | no (±0.55) |
| H3 | tricolon | per 1k words | 0.56 | 0.88 | ↑ +0.32 | no (±0.56) |
| | **collateral** | | | | | |
| K1 | list items | per 1k words | 10.06 | 3.52 | ↓ -6.54 | **yes** (±1.98) |
| K2 | code blocks | per 1k words | 3.47 | 1.90 | ↓ -1.57 | **yes** (±0.62) |
| K3 | opening paragraph | words | 27.72 | 39.75 | ↑ +12.03 | **yes** (±7.71) |
| K4 | grid tables | per 1k words | 0.55 | 0.78 | ↑ +0.24 | no (±0.32) |
| | **context** | | | | | |
| C1 | output length | words | 574.33 | 547.78 | ↓ -26.55 | no (±46.97) |
| C2 | mean paragraph length | words | 31.33 | 56.47 | ↑ +25.14 | **yes** (±3.81) |
| C3 | mean sentence length | words | 15.90 | 21.85 | ↑ +5.95 | **yes** (±1.03) |


*Band is two pooled standard errors of the difference between the arms' means, built from within-prompt variance only: both arms answer the same 12 frozen prompts, so between-prompt spread cancels in the difference and is not noise. At 12 prompts there is no power for significance testing; this is effect size against measured variance.*
