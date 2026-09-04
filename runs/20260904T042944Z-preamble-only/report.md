# Eval report — 20260904T042944Z-preamble-only

- **arm** treatment · rules `R07, R08, R09, R10, R05, R06`
- **style sha256** `95352c77f18488de`
- **model** `claude-opus-5[1m]` · **corpus** v2
- **baseline** 20260903T202317Z-v2-control (control)
- **cost** $2.95 · **failed samples** 0


## Substrate A  (n=36 control → n=36 treatment)

| id | metric | unit | control | this run | delta | cleared band? |
|---|---|---|---:|---:|---:|---|
| | **suppressed** | | | | | |
| S1 | one-sentence paragraphs | % of paragraphs | 34.10 | 12.22 | ↓ -21.88 | **yes** (±6.27) |
| S2 | long sentence then punch | % of paragraphs | 7.26 | 5.05 | ↓ -2.20 | no (±3.53) |
| S3 | That/This pivot opener | % of sentences | 4.36 | 3.06 | ↓ -1.30 | no (±2.18) |
| S4a | headers | per 1k words | 7.39 | 4.45 | ↓ -2.94 | **yes** (±0.70) |
| S4b | table rows | per 1k words | 4.60 | 6.11 | ↑ +1.51 | no (±1.76) |
| S5 | inline bold emphasis | per 1k words | 0.64 | 0.00 | ↓ -0.64 | **yes** (±0.25) |
| S6 | em-dash | per 1k words | 12.01 | 0.34 | ↓ -11.68 | **yes** (±1.10) |
| S7 | terminal service offer | % of samples | 22.22 | 0.00 | ↓ -22.22 | **yes** (±13.61) |
| S8 | arrow as connective | per 1k words | 0.85 | 0.07 | ↓ -0.79 | **yes** (±0.38) |
| S9 | unattached label | per 1k words | 0.52 | 0.00 | ↓ -0.52 | no (±0.86) |
| | **held-out** | | | | | |
| H1 | hedge density | per 1k words | 1.04 | 0.98 | ↓ -0.06 | no (±0.61) |
| H2 | intensifier density | per 1k words | 1.24 | 1.19 | ↓ -0.05 | no (±0.54) |
| H3 | tricolon | per 1k words | 0.56 | 0.64 | ↑ +0.08 | no (±0.57) |
| | **collateral** | | | | | |
| K1 | list items | per 1k words | 10.06 | 3.70 | ↓ -6.36 | **yes** (±1.82) |
| K2 | code blocks | per 1k words | 3.47 | 2.00 | ↓ -1.47 | **yes** (±0.74) |
| K3 | opening paragraph | words | 27.72 | 42.14 | ↑ +14.42 | **yes** (±8.22) |
| K4 | grid tables | per 1k words | 0.55 | 0.86 | ↑ +0.32 | no (±0.33) |
| | **context** | | | | | |
| C1 | output length | words | 574.33 | 555.17 | ↓ -19.17 | no (±41.95) |
| C2 | mean paragraph length | words | 31.33 | 54.01 | ↑ +22.68 | **yes** (±2.77) |
| C3 | mean sentence length | words | 15.90 | 21.17 | ↑ +5.27 | **yes** (±1.02) |


*Band is two pooled standard errors of the difference between the arms' means, built from within-prompt variance only: both arms answer the same 12 frozen prompts, so between-prompt spread cancels in the difference and is not noise. At 12 prompts there is no power for significance testing; this is effect size against measured variance.*
