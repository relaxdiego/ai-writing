# Eval report — 20260904T032924Z-guide-as-shipped

- **arm** treatment · rules `R07, R08, R09, R10, R05, R06`
- **style sha256** `f20b1ebd89e14ddd`
- **model** `claude-opus-5[1m]` · **corpus** v2
- **baseline** 20260903T231128Z-R10-scan-not-length (treatment)
- **cost** $2.93 · **failed samples** 0


## Substrate A  (n=36 control → n=36 treatment)

| id | metric | unit | control | this run | delta | cleared band? |
|---|---|---|---:|---:|---:|---|
| | **suppressed** | | | | | |
| S1 | one-sentence paragraphs | % of paragraphs | 18.82 | 13.43 | ↓ -5.39 | **yes** (±5.15) |
| S2 | long sentence then punch | % of paragraphs | 6.91 | 4.95 | ↓ -1.96 | no (±3.54) |
| S3 | That/This pivot opener | % of sentences | 3.65 | 2.18 | ↓ -1.47 | no (±1.55) |
| S4a | headers | per 1k words | 4.35 | 4.94 | ↑ +0.58 | **yes** (±0.49) |
| S4b | table rows | per 1k words | 5.64 | 4.18 | ↓ -1.46 | no (±2.04) |
| S5 | inline bold emphasis | per 1k words | 0.03 | 0.13 | ↑ +0.10 | no (±0.27) |
| S6 | em-dash | per 1k words | 0.04 | 2.48 | ↑ +2.44 | **yes** (±0.72) |
| S7 | terminal service offer | % of samples | 0.00 | 0.00 | · +0.00 | no (±0.00) |
| S8 | arrow as connective | per 1k words | 0.21 | 0.00 | ↓ -0.21 | **yes** (±0.04) |
| S9 | unattached label | per 1k words | 0.00 | 0.00 | · +0.00 | no (±0.00) |
| | **held-out** | | | | | |
| H1 | hedge density | per 1k words | 0.99 | 0.71 | ↓ -0.28 | no (±0.47) |
| H2 | intensifier density | per 1k words | 1.14 | 1.19 | ↑ +0.04 | no (±0.48) |
| H3 | tricolon | per 1k words | 0.88 | 0.40 | ↓ -0.48 | **yes** (±0.47) |
| | **collateral** | | | | | |
| K1 | list items | per 1k words | 3.52 | 4.34 | ↑ +0.81 | no (±1.47) |
| K2 | code blocks | per 1k words | 1.90 | 2.01 | ↑ +0.11 | no (±0.63) |
| K3 | opening paragraph | words | 39.75 | 38.39 | ↓ -1.36 | no (±7.76) |
| K4 | grid tables | per 1k words | 0.78 | 0.64 | ↓ -0.14 | no (±0.31) |
| K5 | em-dash interruption | per 1k words | 0.00 | 0.30 | ↑ +0.30 | no (±0.36) |
| | **context** | | | | | |
| C1 | output length | words | 547.78 | 553.89 | ↑ +6.11 | no (±51.23) |
| C2 | mean paragraph length | words | 56.47 | 55.42 | ↓ -1.05 | no (±4.25) |
| C3 | mean sentence length | words | 21.85 | 21.31 | ↓ -0.54 | no (±1.05) |


*Band is two pooled standard errors of the difference between the arms' means, built from within-prompt variance only: both arms answer the same 12 frozen prompts, so between-prompt spread cancels in the difference and is not noise. At 12 prompts there is no power for significance testing; this is effect size against measured variance.*
