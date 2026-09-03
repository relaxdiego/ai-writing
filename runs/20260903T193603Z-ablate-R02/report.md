# Eval report — 20260903T193603Z-ablate-R02

- **arm** treatment · rules `R04, R05, R06`
- **style sha256** `72ea0582ad436a1f`
- **model** `claude-opus-5[1m]` · **corpus** v1
- **baseline** 20260903T003018Z (control)
- **cost** $3.60 · **failed samples** 0


## Substrate A  (n=36 control → n=36 treatment)

| id | metric | unit | control | this run | delta | cleared band? |
|---|---|---|---:|---:|---:|---|
| | **suppressed** | | | | | |
| S1 | one-sentence paragraphs | % of paragraphs | 29.84 | 11.09 | ↓ -18.76 | **yes** (±5.80) |
| S2 | long sentence then punch | % of paragraphs | 6.87 | 4.76 | ↓ -2.11 | no (±2.82) |
| S3 | That/This pivot opener | % of sentences | 4.86 | 3.85 | ↓ -1.01 | no (±1.95) |
| S4a | headers | per 1k words | 9.00 | 4.15 | ↓ -4.85 | **yes** (±0.86) |
| S4b | table rows | per 1k words | 4.21 | 0.00 | ↓ -4.21 | **yes** (±0.86) |
| S5 | inline bold emphasis | per 1k words | 1.28 | 0.00 | ↓ -1.28 | **yes** (±0.57) |
| S6 | em-dash | per 1k words | 11.96 | 1.66 | ↓ -10.30 | **yes** (±1.51) |
| S7 | terminal service offer | % of samples | 16.67 | 0.00 | ↓ -16.67 | **yes** (±11.11) |
| S8 | arrow as connective | per 1k words | 1.69 | 0.00 | ↓ -1.69 | **yes** (±0.51) |
| S9 | unattached label | per 1k words | 1.43 | 0.00 | ↓ -1.43 | **yes** (±0.48) |
| | **held-out** | | | | | |
| H1 | hedge density | per 1k words | 1.50 | 1.02 | ↓ -0.48 | no (±0.87) |
| H2 | intensifier density | per 1k words | 1.20 | 0.85 | ↓ -0.35 | no (±0.52) |
| H3 | tricolon | per 1k words | 0.54 | 0.66 | ↑ +0.13 | no (±0.48) |
| | **collateral** | | | | | |
| K1 | list items | per 1k words | 10.78 | 2.47 | ↓ -8.31 | **yes** (±1.90) |
| K2 | code blocks | per 1k words | 2.08 | 1.27 | ↓ -0.82 | **yes** (±0.43) |
| K3 | opening paragraph | words | 28.44 | 44.78 | ↑ +16.33 | **yes** (±8.11) |
| K4 | grid tables | per 1k words | 0.60 | 0.00 | ↓ -0.60 | **yes** (±0.17) |
| | **context** | | | | | |
| C1 | output length | words | 641.44 | 502.61 | ↓ -138.83 | **yes** (±45.18) |
| C2 | mean paragraph length | words | 37.57 | 60.51 | ↑ +22.93 | **yes** (±5.35) |
| C3 | mean sentence length | words | 15.64 | 19.53 | ↑ +3.90 | **yes** (±1.01) |


*Band is two pooled standard errors of the difference between the arms' means, built from within-prompt variance only: both arms answer the same 12 frozen prompts, so between-prompt spread cancels in the difference and is not noise. At 12 prompts there is no power for significance testing; this is effect size against measured variance.*
