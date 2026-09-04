# Eval report — 20260904T040350Z-closing-sections-only

- **arm** treatment · rules `R07, R08, R09, R10, R05, R06`
- **style sha256** `606d76eca7049ff2`
- **model** `claude-opus-5[1m]` · **corpus** v2
- **baseline** 20260903T231128Z-R10-scan-not-length (treatment)
- **cost** $3.36 · **failed samples** 0


## Substrate A  (n=36 control → n=36 treatment)

| id | metric | unit | control | this run | delta | cleared band? |
|---|---|---|---:|---:|---:|---|
| | **suppressed** | | | | | |
| S1 | one-sentence paragraphs | % of paragraphs | 18.82 | 20.05 | ↑ +1.23 | no (±5.04) |
| S2 | long sentence then punch | % of paragraphs | 6.91 | 7.19 | ↑ +0.28 | no (±4.03) |
| S3 | That/This pivot opener | % of sentences | 3.65 | 2.26 | ↓ -1.39 | no (±1.70) |
| S4a | headers | per 1k words | 4.35 | 4.48 | ↑ +0.12 | no (±0.55) |
| S4b | table rows | per 1k words | 5.64 | 4.11 | ↓ -1.53 | no (±2.05) |
| S5 | inline bold emphasis | per 1k words | 0.03 | 0.04 | ↑ +0.01 | no (±0.11) |
| S6 | em-dash | per 1k words | 0.04 | 0.06 | ↑ +0.01 | no (±0.14) |
| S7 | terminal service offer | % of samples | 0.00 | 0.00 | · +0.00 | no (±0.00) |
| S8 | arrow as connective | per 1k words | 0.21 | 0.22 | ↑ +0.01 | no (±0.13) |
| S9 | unattached label | per 1k words | 0.00 | 0.04 | ↑ +0.04 | no (±0.07) |
| | **held-out** | | | | | |
| H1 | hedge density | per 1k words | 0.99 | 0.84 | ↓ -0.14 | no (±0.48) |
| H2 | intensifier density | per 1k words | 1.14 | 1.19 | ↑ +0.05 | no (±0.51) |
| H3 | tricolon | per 1k words | 0.88 | 0.65 | ↓ -0.23 | no (±0.55) |
| | **collateral** | | | | | |
| K1 | list items | per 1k words | 3.52 | 4.99 | ↑ +1.47 | **yes** (±1.42) |
| K2 | code blocks | per 1k words | 1.90 | 2.42 | ↑ +0.52 | no (±0.90) |
| K3 | opening paragraph | words | 39.75 | 36.56 | ↓ -3.19 | no (±5.34) |
| K4 | grid tables | per 1k words | 0.78 | 0.64 | ↓ -0.15 | no (±0.34) |
| | **context** | | | | | |
| C1 | output length | words | 547.78 | 573.75 | ↑ +25.97 | no (±40.84) |
| C2 | mean paragraph length | words | 56.47 | 54.98 | ↓ -1.49 | no (±4.62) |
| C3 | mean sentence length | words | 21.85 | 21.21 | ↓ -0.64 | no (±1.07) |


*Band is two pooled standard errors of the difference between the arms' means, built from within-prompt variance only: both arms answer the same 12 frozen prompts, so between-prompt spread cancels in the difference and is not noise. At 12 prompts there is no power for significance testing; this is effect size against measured variance.*
