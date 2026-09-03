# Eval report — 20260903T040710Z-ablate-R03

- **arm** treatment · rules `R02, R04, R05, R06`
- **style sha256** `108ae8328520294c`
- **model** `claude-opus-5[1m]` · **corpus** v1
- **baseline** 20260903T035059Z-R03-R06 (treatment)
- **cost** $6.02 · **failed samples** 0


## Substrate A  (n=36 control → n=36 treatment)

| id | metric | unit | control | this run | delta | cleared band? |
|---|---|---|---:|---:|---:|---|
| | **suppressed** | | | | | |
| S1 | one-sentence paragraphs | % of paragraphs | 7.98 | 6.79 | ↓ -1.19 | no (±6.61) |
| S2 | long sentence then punch | % of paragraphs | 2.99 | 3.09 | ↑ +0.10 | no (±3.14) |
| S3 | That/This pivot opener | % of sentences | 2.18 | 2.32 | ↑ +0.14 | no (±1.76) |
| S4a | headers | per 1k words | 4.00 | 3.44 | ↓ -0.56 | no (±2.58) |
| S4b | table rows | per 1k words | 0.00 | 0.00 | · +0.00 | no (±0.00) |
| S5 | inline bold emphasis | per 1k words | 0.55 | 0.27 | ↓ -0.28 | no (±1.00) |
| S6 | em-dash | per 1k words | 0.97 | 0.59 | ↓ -0.38 | no (±1.27) |
| S7 | terminal service offer | % of samples | 0.00 | 0.00 | · +0.00 | no (±0.00) |
| | **held-out** | | | | | |
| H1 | hedge density | per 1k words | 0.87 | 0.99 | ↑ +0.12 | no (±0.76) |
| H2 | intensifier density | per 1k words | 1.05 | 1.91 | ↑ +0.86 | no (±1.20) |
| H3 | tricolon | per 1k words | 0.78 | 0.76 | ↓ -0.03 | no (±0.64) |
| | **context** | | | | | |
| C1 | output length | words | 534.28 | 533.22 | ↓ -1.06 | no (±137.65) |
| C2 | mean paragraph length | words | 78.75 | 81.20 | ↑ +2.45 | no (±13.92) |
| C3 | mean sentence length | words | 23.73 | 24.59 | ↑ +0.86 | no (±1.88) |

## Substrate B  (n=60 control → n=60 treatment)

| id | metric | unit | control | this run | delta | cleared band? |
|---|---|---|---:|---:|---:|---|
| | **suppressed** | | | | | |
| S1 | one-sentence paragraphs | % of paragraphs | 8.15 | 8.04 | ↓ -0.11 | no (±4.70) |
| S2 | long sentence then punch | % of paragraphs | 4.33 | 3.23 | ↓ -1.10 | no (±3.28) |
| S3 | That/This pivot opener | % of sentences | 2.35 | 2.76 | ↑ +0.41 | no (±1.28) |
| S4a | headers | per 1k words | 3.58 | 3.88 | ↑ +0.30 | no (±1.96) |
| S4b | table rows | per 1k words | 0.00 | 0.00 | · +0.00 | no (±0.00) |
| S5 | inline bold emphasis | per 1k words | 0.60 | 0.80 | ↑ +0.20 | no (±1.04) |
| S6 | em-dash | per 1k words | 1.60 | 1.45 | ↓ -0.16 | no (±1.45) |
| S7 | terminal service offer | % of samples | 0.00 | 0.00 | · +0.00 | no (±0.00) |
| | **held-out** | | | | | |
| H1 | hedge density | per 1k words | 1.32 | 1.33 | ↑ +0.01 | no (±0.79) |
| H2 | intensifier density | per 1k words | 1.00 | 1.40 | ↑ +0.40 | no (±0.59) |
| H3 | tricolon | per 1k words | 0.71 | 0.88 | ↑ +0.17 | no (±0.50) |
| | **context** | | | | | |
| C1 | output length | words | 526.05 | 529.90 | ↑ +3.85 | no (±98.27) |
| C2 | mean paragraph length | words | 79.21 | 81.84 | ↑ +2.64 | no (±11.35) |
| C3 | mean sentence length | words | 24.54 | 24.96 | ↑ +0.42 | no (±1.29) |


*Band is two pooled standard errors of the difference between the arms' means. At 12 prompts there is no power for significance testing; this is effect size against measured variance.*
