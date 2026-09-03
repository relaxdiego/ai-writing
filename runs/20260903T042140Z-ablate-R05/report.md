# Eval report — 20260903T042140Z-ablate-R05

- **arm** treatment · rules `R02, R04, R06`
- **style sha256** `a4d6ab4ed303fd7c`
- **model** `claude-opus-5[1m]` · **corpus** v1
- **baseline** 20260903T003018Z (control)
- **cost** $5.53 · **failed samples** 0


## Substrate A  (n=36 control → n=36 treatment)

| id | metric | unit | control | this run | delta | cleared band? |
|---|---|---|---:|---:|---:|---|
| | **suppressed** | | | | | |
| S1 | one-sentence paragraphs | % of paragraphs | 31.54 | 7.19 | ↓ -24.35 | **yes** (±8.24) |
| S2 | long sentence then punch | % of paragraphs | 9.38 | 7.64 | ↓ -1.74 | no (±8.46) |
| S3 | That/This pivot opener | % of sentences | 4.80 | 1.82 | ↓ -2.98 | **yes** (±1.78) |
| S4a | headers | per 1k words | 9.00 | 3.54 | ↓ -5.45 | **yes** (±2.55) |
| S4b | table rows | per 1k words | 4.21 | 0.00 | ↓ -4.21 | **yes** (±2.17) |
| S5 | inline bold emphasis | per 1k words | 3.97 | 0.00 | ↓ -3.97 | **yes** (±1.28) |
| S6 | em-dash | per 1k words | 11.96 | 0.81 | ↓ -11.15 | **yes** (±2.11) |
| S7 | terminal service offer | % of samples | 16.67 | 16.67 | · +0.00 | no (±17.82) |
| | **held-out** | | | | | |
| H1 | hedge density | per 1k words | 1.50 | 1.12 | ↓ -0.39 | no (±0.86) |
| H2 | intensifier density | per 1k words | 1.20 | 1.40 | ↑ +0.20 | no (±0.87) |
| H3 | tricolon | per 1k words | 0.54 | 1.13 | ↑ +0.59 | no (±0.76) |
| | **collateral** | | | | | |
| K1 | list items | per 1k words | 10.78 | 1.67 | ↓ -9.10 | **yes** (±3.36) |
| K2 | code blocks | per 1k words | 2.08 | 0.98 | ↓ -1.11 | no (±1.43) |
| | **context** | | | | | |
| C1 | output length | words | 641.44 | 506.03 | ↓ -135.42 | no (±154.08) |
| C2 | mean paragraph length | words | 36.87 | 74.83 | ↑ +37.96 | **yes** (±9.19) |
| C3 | mean sentence length | words | 15.48 | 24.09 | ↑ +8.61 | **yes** (±1.56) |

## Substrate B  (n=60 control → n=60 treatment)

| id | metric | unit | control | this run | delta | cleared band? |
|---|---|---|---:|---:|---:|---|
| | **suppressed** | | | | | |
| S1 | one-sentence paragraphs | % of paragraphs | 31.56 | 7.39 | ↓ -24.17 | **yes** (±6.53) |
| S2 | long sentence then punch | % of paragraphs | 8.06 | 4.00 | ↓ -4.06 | no (±4.15) |
| S3 | That/This pivot opener | % of sentences | 3.76 | 3.24 | ↓ -0.52 | no (±1.62) |
| S4a | headers | per 1k words | 10.30 | 4.01 | ↓ -6.29 | **yes** (±2.29) |
| S4b | table rows | per 1k words | 4.20 | 0.37 | ↓ -3.82 | **yes** (±1.95) |
| S5 | inline bold emphasis | per 1k words | 6.81 | 0.64 | ↓ -6.17 | **yes** (±1.48) |
| S6 | em-dash | per 1k words | 10.75 | 1.12 | ↓ -9.63 | **yes** (±1.33) |
| S7 | terminal service offer | % of samples | 23.33 | 8.33 | ↓ -15.00 | **yes** (±13.15) |
| | **held-out** | | | | | |
| H1 | hedge density | per 1k words | 2.04 | 1.63 | ↓ -0.42 | no (±0.95) |
| H2 | intensifier density | per 1k words | 1.87 | 1.80 | ↓ -0.07 | no (±0.84) |
| H3 | tricolon | per 1k words | 0.57 | 0.64 | ↑ +0.07 | no (±0.43) |
| | **collateral** | | | | | |
| K1 | list items | per 1k words | 12.78 | 0.64 | ↓ -12.14 | **yes** (±2.26) |
| K2 | code blocks | per 1k words | 2.23 | 1.12 | ↓ -1.11 | no (±1.25) |
| | **context** | | | | | |
| C1 | output length | words | 617.87 | 515.42 | ↓ -102.45 | no (±104.50) |
| C2 | mean paragraph length | words | 35.47 | 76.58 | ↑ +41.11 | **yes** (±9.05) |
| C3 | mean sentence length | words | 15.64 | 23.49 | ↑ +7.86 | **yes** (±1.29) |


*Band is two pooled standard errors of the difference between the arms' means. At 12 prompts there is no power for significance testing; this is effect size against measured variance.*
