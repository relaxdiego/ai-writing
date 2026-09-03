# Eval report — 20260903T035059Z-R03-R06

- **arm** treatment · rules `R02, R03, R04, R05, R06`
- **style sha256** `7695fb2eade6790e`
- **model** `claude-opus-5[1m]` · **corpus** v1
- **baseline** 20260903T031737Z-R02 (treatment)
- **cost** $6.56 · **failed samples** 0


## Substrate A  (n=36 control → n=36 treatment)

| id | metric | unit | control | this run | delta | cleared band? |
|---|---|---|---:|---:|---:|---|
| | **suppressed** | | | | | |
| S1 | one-sentence paragraphs | % of paragraphs | 7.99 | 7.98 | ↓ -0.01 | no (±5.75) |
| S2 | long sentence then punch | % of paragraphs | 5.54 | 2.99 | ↓ -2.55 | no (±6.20) |
| S3 | That/This pivot opener | % of sentences | 1.00 | 2.18 | ↑ +1.18 | no (±1.34) |
| S4a | headers | per 1k words | 4.47 | 4.00 | ↓ -0.47 | no (±2.62) |
| S4b | table rows | per 1k words | 2.16 | 0.00 | ↓ -2.16 | **yes** (±1.78) |
| S5 | inline bold emphasis | per 1k words | 0.88 | 0.55 | ↓ -0.32 | no (±1.06) |
| S6 | em-dash | per 1k words | 8.44 | 0.97 | ↓ -7.47 | **yes** (±1.65) |
| S7 | terminal service offer | % of samples | 8.33 | 0.00 | ↓ -8.33 | no (±9.34) |
| | **held-out** | | | | | |
| H1 | hedge density | per 1k words | 1.30 | 0.87 | ↓ -0.43 | no (±0.70) |
| H2 | intensifier density | per 1k words | 1.44 | 1.05 | ↓ -0.38 | no (±0.81) |
| H3 | tricolon | per 1k words | 0.55 | 0.78 | ↑ +0.24 | no (±0.59) |
| | **context** | | | | | |
| C1 | output length | words | 637.17 | 534.28 | ↓ -102.89 | no (±159.26) |
| C2 | mean paragraph length | words | 74.99 | 78.75 | ↑ +3.75 | no (±11.52) |
| C3 | mean sentence length | words | 25.82 | 23.73 | ↓ -2.09 | **yes** (±1.84) |

## Substrate B  (n=60 control → n=60 treatment)

| id | metric | unit | control | this run | delta | cleared band? |
|---|---|---|---:|---:|---:|---|
| | **suppressed** | | | | | |
| S1 | one-sentence paragraphs | % of paragraphs | 7.01 | 8.15 | ↑ +1.14 | no (±4.20) |
| S2 | long sentence then punch | % of paragraphs | 6.03 | 4.33 | ↓ -1.69 | no (±4.55) |
| S3 | That/This pivot opener | % of sentences | 1.59 | 2.35 | ↑ +0.76 | no (±1.16) |
| S4a | headers | per 1k words | 5.33 | 3.58 | ↓ -1.75 | no (±2.14) |
| S4b | table rows | per 1k words | 1.77 | 0.00 | ↓ -1.77 | **yes** (±1.55) |
| S5 | inline bold emphasis | per 1k words | 0.86 | 0.60 | ↓ -0.26 | no (±0.90) |
| S6 | em-dash | per 1k words | 7.87 | 1.60 | ↓ -6.27 | **yes** (±1.33) |
| S7 | terminal service offer | % of samples | 5.00 | 0.00 | ↓ -5.00 | no (±5.67) |
| | **held-out** | | | | | |
| H1 | hedge density | per 1k words | 1.46 | 1.32 | ↓ -0.14 | no (±0.79) |
| H2 | intensifier density | per 1k words | 2.22 | 1.00 | ↓ -1.22 | **yes** (±0.67) |
| H3 | tricolon | per 1k words | 0.64 | 0.71 | ↑ +0.07 | no (±0.50) |
| | **context** | | | | | |
| C1 | output length | words | 568.05 | 526.05 | ↓ -42.00 | no (±100.62) |
| C2 | mean paragraph length | words | 78.39 | 79.21 | ↑ +0.82 | no (±9.34) |
| C3 | mean sentence length | words | 26.15 | 24.54 | ↓ -1.62 | **yes** (±1.33) |


*Band is two pooled standard errors of the difference between the arms' means. At 12 prompts there is no power for significance testing; this is effect size against measured variance.*
