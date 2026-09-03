# Eval report — 20260903T035059Z-R03-R06

- **arm** treatment · rules `R02, R03, R04, R05, R06`
- **style sha256** `7695fb2eade6790e`
- **model** `claude-opus-5[1m]` · **corpus** v1
- **baseline** 20260903T003018Z (control)
- **cost** $6.56 · **failed samples** 0


## Substrate A  (n=36 control → n=36 treatment)

| id | metric | unit | control | this run | delta | cleared band? |
|---|---|---|---:|---:|---:|---|
| | **suppressed** | | | | | |
| S1 | one-sentence paragraphs | % of paragraphs | 31.54 | 7.98 | ↓ -23.56 | **yes** (±8.69) |
| S2 | long sentence then punch | % of paragraphs | 9.38 | 2.99 | ↓ -6.39 | **yes** (±6.03) |
| S3 | That/This pivot opener | % of sentences | 4.80 | 2.18 | ↓ -2.62 | **yes** (±1.92) |
| S4a | headers | per 1k words | 9.00 | 4.00 | ↓ -5.00 | **yes** (±2.68) |
| S4b | table rows | per 1k words | 4.21 | 0.00 | ↓ -4.21 | **yes** (±2.17) |
| S5 | inline bold emphasis | per 1k words | 3.97 | 0.55 | ↓ -3.42 | **yes** (±1.53) |
| S6 | em-dash | per 1k words | 11.96 | 0.97 | ↓ -10.99 | **yes** (±2.12) |
| S7 | terminal service offer | % of samples | 16.67 | 0.00 | ↓ -16.67 | **yes** (±12.60) |
| | **held-out** | | | | | |
| H1 | hedge density | per 1k words | 1.50 | 0.87 | ↓ -0.63 | no (±0.77) |
| H2 | intensifier density | per 1k words | 1.20 | 1.05 | ↓ -0.15 | no (±0.79) |
| H3 | tricolon | per 1k words | 0.54 | 0.78 | ↑ +0.25 | no (±0.56) |
| | **collateral** | | | | | |
| K1 | list items | per 1k words | 10.78 | 1.33 | ↓ -9.44 | **yes** (±3.34) |
| K2 | code blocks | per 1k words | 2.08 | 1.16 | ↓ -0.92 | no (±1.47) |
| K3 | opening paragraph | words | 28.44 | 71.64 | ↑ +43.19 | **yes** (±16.95) |
| | **context** | | | | | |
| C1 | output length | words | 641.44 | 534.28 | ↓ -107.17 | no (±159.66) |
| C2 | mean paragraph length | words | 36.87 | 78.75 | ↑ +41.88 | **yes** (±10.99) |
| C3 | mean sentence length | words | 15.48 | 23.73 | ↑ +8.25 | **yes** (±1.76) |

## Substrate B  (n=60 control → n=60 treatment)

| id | metric | unit | control | this run | delta | cleared band? |
|---|---|---|---:|---:|---:|---|
| | **suppressed** | | | | | |
| S1 | one-sentence paragraphs | % of paragraphs | 31.56 | 8.15 | ↓ -23.41 | **yes** (±6.72) |
| S2 | long sentence then punch | % of paragraphs | 8.06 | 4.33 | ↓ -3.73 | no (±4.26) |
| S3 | That/This pivot opener | % of sentences | 3.76 | 2.35 | ↓ -1.41 | no (±1.52) |
| S4a | headers | per 1k words | 10.30 | 3.58 | ↓ -6.72 | **yes** (±2.15) |
| S4b | table rows | per 1k words | 4.20 | 0.00 | ↓ -4.20 | **yes** (±1.88) |
| S5 | inline bold emphasis | per 1k words | 6.81 | 0.60 | ↓ -6.21 | **yes** (±1.45) |
| S6 | em-dash | per 1k words | 10.75 | 1.60 | ↓ -9.14 | **yes** (±1.50) |
| S7 | terminal service offer | % of samples | 23.33 | 0.00 | ↓ -23.33 | **yes** (±11.01) |
| | **held-out** | | | | | |
| H1 | hedge density | per 1k words | 2.04 | 1.32 | ↓ -0.72 | no (±0.93) |
| H2 | intensifier density | per 1k words | 1.87 | 1.00 | ↓ -0.87 | **yes** (±0.68) |
| H3 | tricolon | per 1k words | 0.57 | 0.71 | ↑ +0.14 | no (±0.48) |
| | **collateral** | | | | | |
| K1 | list items | per 1k words | 12.78 | 1.10 | ↓ -11.69 | **yes** (±2.34) |
| K2 | code blocks | per 1k words | 2.23 | 1.03 | ↓ -1.19 | no (±1.24) |
| K3 | opening paragraph | words | 27.92 | 70.15 | ↑ +42.23 | **yes** (±12.92) |
| | **context** | | | | | |
| C1 | output length | words | 617.87 | 526.05 | ↓ -91.82 | no (±104.44) |
| C2 | mean paragraph length | words | 35.47 | 79.21 | ↑ +43.74 | **yes** (±8.32) |
| C3 | mean sentence length | words | 15.64 | 24.54 | ↑ +8.90 | **yes** (±1.21) |


*Band is two pooled standard errors of the difference between the arms' means. At 12 prompts there is no power for significance testing; this is effect size against measured variance.*
