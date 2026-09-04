# Eval report — 20260904T042944Z-preamble-only

- **arm** treatment · rules `R07, R08, R09, R10, R05, R06`
- **style sha256** `95352c77f18488de`
- **model** `claude-opus-5[1m]` · **corpus** v2
- **baseline** 20260903T231128Z-R10-scan-not-length (treatment)
- **cost** $2.95 · **failed samples** 0


## Substrate A  (n=36 control → n=36 treatment)

| id | metric | unit | control | this run | delta | cleared band? |
|---|---|---|---:|---:|---:|---|
| | **suppressed** | | | | | |
| S1 | one-sentence paragraphs | % of paragraphs | 18.82 | 12.22 | ↓ -6.60 | **yes** (±4.93) |
| S2 | long sentence then punch | % of paragraphs | 6.91 | 5.05 | ↓ -1.85 | no (±3.47) |
| S3 | That/This pivot opener | % of sentences | 3.65 | 3.06 | ↓ -0.59 | no (±2.08) |
| S4a | headers | per 1k words | 4.35 | 4.45 | ↑ +0.10 | no (±0.46) |
| S4b | table rows | per 1k words | 5.64 | 6.11 | ↑ +0.47 | no (±2.01) |
| S5 | inline bold emphasis | per 1k words | 0.03 | 0.00 | ↓ -0.03 | no (±0.06) |
| S6 | em-dash | per 1k words | 0.04 | 0.13 | ↑ +0.09 | no (±0.16) |
| S7 | terminal service offer | % of samples | 0.00 | 0.00 | · +0.00 | no (±0.00) |
| S8 | arrow as connective | per 1k words | 0.21 | 0.07 | ↓ -0.14 | **yes** (±0.14) |
| S9 | unattached label | per 1k words | 0.00 | 0.00 | · +0.00 | no (±0.00) |
| | **held-out** | | | | | |
| H1 | hedge density | per 1k words | 0.99 | 0.98 | ↓ -0.00 | no (±0.55) |
| H2 | intensifier density | per 1k words | 1.14 | 1.19 | ↑ +0.05 | no (±0.50) |
| H3 | tricolon | per 1k words | 0.88 | 0.64 | ↓ -0.24 | no (±0.51) |
| | **collateral** | | | | | |
| K1 | list items | per 1k words | 3.52 | 3.70 | ↑ +0.17 | no (±1.38) |
| K2 | code blocks | per 1k words | 1.90 | 2.00 | ↑ +0.10 | no (±0.65) |
| K3 | opening paragraph | words | 39.75 | 42.14 | ↑ +2.39 | no (±7.15) |
| K4 | grid tables | per 1k words | 0.78 | 0.86 | ↑ +0.08 | no (±0.32) |
| K5 | em-dash interruption | per 1k words | 0.00 | 0.15 | ↑ +0.15 | no (±0.31) |
| | **context** | | | | | |
| C1 | output length | words | 547.78 | 555.17 | ↑ +7.39 | no (±43.66) |
| C2 | mean paragraph length | words | 56.47 | 54.01 | ↓ -2.46 | no (±3.95) |
| C3 | mean sentence length | words | 21.85 | 21.17 | ↓ -0.68 | no (±1.06) |


*Band is two pooled standard errors of the difference between the arms' means, built from within-prompt variance only: both arms answer the same 12 frozen prompts, so between-prompt spread cancels in the difference and is not noise. At 12 prompts there is no power for significance testing; this is effect size against measured variance.*
