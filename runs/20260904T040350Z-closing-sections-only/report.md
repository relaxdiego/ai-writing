# Eval report — 20260904T040350Z-closing-sections-only

- **arm** treatment · rules `R07, R08, R09, R10, R05, R06`
- **style sha256** `606d76eca7049ff2`
- **model** `claude-opus-5[1m]` · **corpus** v2
- **baseline** 20260903T202317Z-v2-control (control)
- **cost** $3.36 · **failed samples** 0


## Substrate A  (n=36 control → n=36 treatment)

| id | metric | unit | control | this run | delta | cleared band? |
|---|---|---|---:|---:|---:|---|
| | **suppressed** | | | | | |
| S1 | one-sentence paragraphs | % of paragraphs | 34.10 | 20.05 | ↓ -14.05 | **yes** (±6.35) |
| S2 | long sentence then punch | % of paragraphs | 7.26 | 7.19 | ↓ -0.07 | no (±4.08) |
| S3 | That/This pivot opener | % of sentences | 4.36 | 2.26 | ↓ -2.11 | **yes** (±1.81) |
| S4a | headers | per 1k words | 7.39 | 4.48 | ↓ -2.91 | **yes** (±0.76) |
| S4b | table rows | per 1k words | 4.60 | 4.11 | ↓ -0.50 | no (±1.80) |
| S5 | inline bold emphasis | per 1k words | 0.64 | 0.04 | ↓ -0.60 | **yes** (±0.27) |
| S6 | em-dash | per 1k words | 12.01 | 0.06 | ↓ -11.96 | **yes** (±1.04) |
| S7 | terminal service offer | % of samples | 22.22 | 0.00 | ↓ -22.22 | **yes** (±13.61) |
| S8 | arrow as connective | per 1k words | 0.85 | 0.22 | ↓ -0.63 | **yes** (±0.38) |
| S9 | unattached label | per 1k words | 0.52 | 0.04 | ↓ -0.49 | no (±0.86) |
| | **held-out** | | | | | |
| H1 | hedge density | per 1k words | 1.04 | 0.84 | ↓ -0.20 | no (±0.54) |
| H2 | intensifier density | per 1k words | 1.24 | 1.19 | ↓ -0.04 | no (±0.54) |
| H3 | tricolon | per 1k words | 0.56 | 0.65 | ↑ +0.08 | no (±0.60) |
| | **collateral** | | | | | |
| K1 | list items | per 1k words | 10.06 | 4.99 | ↓ -5.07 | **yes** (±1.84) |
| K2 | code blocks | per 1k words | 3.47 | 2.42 | ↓ -1.05 | **yes** (±0.97) |
| K3 | opening paragraph | words | 27.72 | 36.56 | ↑ +8.83 | **yes** (±6.71) |
| K4 | grid tables | per 1k words | 0.55 | 0.64 | ↑ +0.09 | no (±0.35) |
| | **context** | | | | | |
| C1 | output length | words | 574.33 | 573.75 | ↓ -0.58 | no (±39.02) |
| C2 | mean paragraph length | words | 31.33 | 54.98 | ↑ +23.65 | **yes** (±3.68) |
| C3 | mean sentence length | words | 15.90 | 21.21 | ↑ +5.31 | **yes** (±1.03) |


*Band is two pooled standard errors of the difference between the arms' means, built from within-prompt variance only: both arms answer the same 12 frozen prompts, so between-prompt spread cancels in the difference and is not noise. At 12 prompts there is no power for significance testing; this is effect size against measured variance.*
