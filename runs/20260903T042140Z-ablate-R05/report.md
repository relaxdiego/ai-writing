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
| S1 | one-sentence paragraphs | % of paragraphs | 29.84 | 6.54 | ↓ -23.30 | **yes** (±4.50) |
| S2 | long sentence then punch | % of paragraphs | 6.87 | 5.02 | ↓ -1.85 | no (±3.49) |
| S3 | That/This pivot opener | % of sentences | 4.86 | 1.75 | ↓ -3.10 | **yes** (±1.63) |
| S4a | headers | per 1k words | 9.00 | 3.54 | ↓ -5.45 | **yes** (±0.86) |
| S4b | table rows | per 1k words | 4.21 | 0.00 | ↓ -4.21 | **yes** (±0.86) |
| S5 | inline bold emphasis | per 1k words | 1.28 | 0.00 | ↓ -1.28 | **yes** (±0.57) |
| S6 | em-dash | per 1k words | 11.96 | 0.81 | ↓ -11.15 | **yes** (±1.35) |
| S7 | terminal service offer | % of samples | 16.67 | 16.67 | · +0.00 | no (±16.67) |
| S8 | arrow as connective | per 1k words | 1.69 | 0.00 | ↓ -1.69 | **yes** (±0.51) |
| S9 | unattached label | per 1k words | 1.43 | 0.00 | ↓ -1.43 | **yes** (±0.48) |
| | **held-out** | | | | | |
| H1 | hedge density | per 1k words | 1.50 | 1.12 | ↓ -0.39 | no (±0.82) |
| H2 | intensifier density | per 1k words | 1.20 | 1.40 | ↑ +0.20 | no (±0.70) |
| H3 | tricolon | per 1k words | 0.54 | 1.13 | ↑ +0.59 | **yes** (±0.55) |
| | **collateral** | | | | | |
| K1 | list items | per 1k words | 10.78 | 1.67 | ↓ -9.10 | **yes** (±1.77) |
| K2 | code blocks | per 1k words | 2.08 | 0.98 | ↓ -1.11 | **yes** (±0.39) |
| K3 | opening paragraph | words | 28.44 | 66.03 | ↑ +37.58 | **yes** (±11.74) |
| K4 | grid tables | per 1k words | 0.60 | 0.00 | ↓ -0.60 | **yes** (±0.17) |
| | **context** | | | | | |
| C1 | output length | words | 641.44 | 506.03 | ↓ -135.42 | **yes** (±43.14) |
| C2 | mean paragraph length | words | 37.57 | 75.20 | ↑ +37.63 | **yes** (±5.78) |
| C3 | mean sentence length | words | 15.64 | 24.15 | ↑ +8.52 | **yes** (±1.06) |

## Substrate B  (n=60 control → n=60 treatment)

| id | metric | unit | control | this run | delta | cleared band? |
|---|---|---|---:|---:|---:|---|
| | **suppressed** | | | | | |
| S1 | one-sentence paragraphs | % of paragraphs | 29.85 | 7.39 | ↓ -22.46 | **yes** (±3.78) |
| S2 | long sentence then punch | % of paragraphs | 6.58 | 3.08 | ↓ -3.50 | **yes** (±2.84) |
| S3 | That/This pivot opener | % of sentences | 3.79 | 3.16 | ↓ -0.63 | no (±1.28) |
| S4a | headers | per 1k words | 10.30 | 4.01 | ↓ -6.29 | **yes** (±0.59) |
| S4b | table rows | per 1k words | 4.20 | 0.37 | ↓ -3.82 | **yes** (±1.02) |
| S5 | inline bold emphasis | per 1k words | 2.00 | 0.00 | ↓ -2.00 | **yes** (±0.62) |
| S6 | em-dash | per 1k words | 10.75 | 1.12 | ↓ -9.63 | **yes** (±1.03) |
| S7 | terminal service offer | % of samples | 23.33 | 8.33 | ↓ -15.00 | **yes** (±11.55) |
| S8 | arrow as connective | per 1k words | 0.91 | 0.00 | ↓ -0.91 | **yes** (±0.33) |
| S9 | unattached label | per 1k words | 0.59 | 0.00 | ↓ -0.59 | **yes** (±0.38) |
| | **held-out** | | | | | |
| H1 | hedge density | per 1k words | 2.04 | 1.63 | ↓ -0.42 | no (±0.70) |
| H2 | intensifier density | per 1k words | 1.87 | 1.80 | ↓ -0.07 | no (±0.68) |
| H3 | tricolon | per 1k words | 0.57 | 0.64 | ↑ +0.07 | no (±0.23) |
| | **collateral** | | | | | |
| K1 | list items | per 1k words | 12.78 | 0.64 | ↓ -12.14 | **yes** (±1.13) |
| K2 | code blocks | per 1k words | 2.23 | 1.12 | ↓ -1.11 | **yes** (±0.38) |
| K3 | opening paragraph | words | 27.92 | 61.27 | ↑ +33.35 | **yes** (±8.12) |
| K4 | grid tables | per 1k words | 0.48 | 0.04 | ↓ -0.44 | **yes** (±0.12) |
| | **context** | | | | | |
| C1 | output length | words | 617.87 | 515.42 | ↓ -102.45 | **yes** (±24.77) |
| C2 | mean paragraph length | words | 36.24 | 76.58 | ↑ +40.33 | **yes** (±4.86) |
| C3 | mean sentence length | words | 15.86 | 23.49 | ↑ +7.63 | **yes** (±0.87) |


*Band is two pooled standard errors of the difference between the arms' means, built from within-prompt variance only: both arms answer the same 12 frozen prompts, so between-prompt spread cancels in the difference and is not noise. At 12 prompts there is no power for significance testing; this is effect size against measured variance.*
