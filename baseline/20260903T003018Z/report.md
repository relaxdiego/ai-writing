# Eval report — 20260903T003018Z

- **arm** control
- **style sha256** `—`
- **model** `claude-opus-5[1m]` · **corpus** v1
- **baseline** 20260903T003018Z (control)
- **cost** $6.60 · **failed samples** 0


## Substrate A  (n=36 control → n=36 treatment)

| id | metric | unit | control | this run | delta | cleared band? |
|---|---|---|---:|---:|---:|---|
| | **suppressed** | | | | | |
| S1 | one-sentence paragraphs | % of paragraphs | 31.54 | 31.54 | · +0.00 | no (±5.72) |
| S2 | long sentence then punch | % of paragraphs | 6.62 | 6.62 | · +0.00 | no (±3.25) |
| S3 | That/This pivot opener | % of sentences | 4.80 | 4.80 | · +0.00 | no (±1.98) |
| S4a | headers | per 1k words | 9.00 | 9.00 | · +0.00 | no (±1.13) |
| S4b | table rows | per 1k words | 4.21 | 4.21 | · +0.00 | no (±1.21) |
| S5 | inline bold emphasis | per 1k words | 3.97 | 3.97 | · +0.00 | no (±1.71) |
| S6 | em-dash | per 1k words | 11.96 | 11.96 | · +0.00 | no (±1.61) |
| S7 | terminal service offer | % of samples | 16.67 | 16.67 | · +0.00 | no (±15.71) |
| | **held-out** | | | | | |
| H1 | hedge density | per 1k words | 1.50 | 1.50 | · +0.00 | no (±0.88) |
| H2 | intensifier density | per 1k words | 1.20 | 1.20 | · +0.00 | no (±0.57) |
| H3 | tricolon | per 1k words | 0.54 | 0.54 | · +0.00 | no (±0.42) |
| | **collateral** | | | | | |
| K1 | list items | per 1k words | 10.78 | 10.78 | · +0.00 | no (±2.34) |
| K2 | code blocks | per 1k words | 2.08 | 2.08 | · +0.00 | no (±0.51) |
| K3 | opening paragraph | words | 28.44 | 28.44 | · +0.00 | no (±4.82) |
| K4 | grid tables | per 1k words | 0.60 | 0.60 | · +0.00 | no (±0.25) |
| | **context** | | | | | |
| C1 | output length | words | 641.44 | 641.44 | · +0.00 | no (±53.77) |
| C2 | mean paragraph length | words | 36.87 | 36.87 | · +0.00 | no (±5.64) |
| C3 | mean sentence length | words | 15.48 | 15.48 | · +0.00 | no (±1.09) |

## Substrate B  (n=60 control → n=60 treatment)

| id | metric | unit | control | this run | delta | cleared band? |
|---|---|---|---:|---:|---:|---|
| | **suppressed** | | | | | |
| S1 | one-sentence paragraphs | % of paragraphs | 31.56 | 31.56 | · +0.00 | no (±5.06) |
| S2 | long sentence then punch | % of paragraphs | 6.33 | 6.33 | · +0.00 | no (±3.32) |
| S3 | That/This pivot opener | % of sentences | 3.76 | 3.76 | · +0.00 | no (±1.25) |
| S4a | headers | per 1k words | 10.30 | 10.30 | · +0.00 | no (±0.78) |
| S4b | table rows | per 1k words | 4.20 | 4.20 | · +0.00 | no (±1.23) |
| S5 | inline bold emphasis | per 1k words | 6.81 | 6.81 | · +0.00 | no (±1.61) |
| S6 | em-dash | per 1k words | 10.75 | 10.75 | · +0.00 | no (±1.17) |
| S7 | terminal service offer | % of samples | 23.33 | 23.33 | · +0.00 | no (±12.91) |
| | **held-out** | | | | | |
| H1 | hedge density | per 1k words | 2.04 | 2.04 | · +0.00 | no (±0.69) |
| H2 | intensifier density | per 1k words | 1.87 | 1.87 | · +0.00 | no (±0.65) |
| H3 | tricolon | per 1k words | 0.57 | 0.57 | · +0.00 | no (±0.19) |
| | **collateral** | | | | | |
| K1 | list items | per 1k words | 12.78 | 12.78 | · +0.00 | no (±1.40) |
| K2 | code blocks | per 1k words | 2.23 | 2.23 | · +0.00 | no (±0.50) |
| K3 | opening paragraph | words | 27.92 | 27.92 | · +0.00 | no (±4.47) |
| K4 | grid tables | per 1k words | 0.48 | 0.48 | · +0.00 | no (±0.14) |
| | **context** | | | | | |
| C1 | output length | words | 617.87 | 617.87 | · +0.00 | no (±25.16) |
| C2 | mean paragraph length | words | 35.47 | 35.47 | · +0.00 | no (±3.30) |
| C3 | mean sentence length | words | 15.64 | 15.64 | · +0.00 | no (±1.01) |


*Band is two pooled standard errors of the difference between the arms' means, built from within-prompt variance only: both arms answer the same 12 frozen prompts, so between-prompt spread cancels in the difference and is not noise. At 12 prompts there is no power for significance testing; this is effect size against measured variance.*
