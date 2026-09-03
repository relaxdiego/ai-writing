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
| S1 | one-sentence paragraphs | % of paragraphs | 31.54 | 31.54 | · +0.00 | no (±10.81) |
| S2 | long sentence then punch | % of paragraphs | 9.38 | 9.38 | · +0.00 | no (±8.08) |
| S3 | That/This pivot opener | % of sentences | 4.80 | 4.80 | · +0.00 | no (±2.16) |
| S4a | headers | per 1k words | 9.00 | 9.00 | · +0.00 | no (±2.59) |
| S4b | table rows | per 1k words | 4.21 | 4.21 | · +0.00 | no (±3.07) |
| S5 | inline bold emphasis | per 1k words | 3.97 | 3.97 | · +0.00 | no (±1.80) |
| S6 | em-dash | per 1k words | 11.96 | 11.96 | · +0.00 | no (±2.67) |
| S7 | terminal service offer | % of samples | 16.67 | 16.67 | · +0.00 | no (±17.82) |
| | **held-out** | | | | | |
| H1 | hedge density | per 1k words | 1.50 | 1.50 | · +0.00 | no (±0.94) |
| H2 | intensifier density | per 1k words | 1.20 | 1.20 | · +0.00 | no (±0.82) |
| H3 | tricolon | per 1k words | 0.54 | 0.54 | · +0.00 | no (±0.52) |
| | **collateral** | | | | | |
| K1 | list items | per 1k words | 10.78 | 10.78 | · +0.00 | no (±4.21) |
| K2 | code blocks | per 1k words | 2.08 | 2.08 | · +0.00 | no (±1.69) |
| K3 | opening paragraph | words | 28.44 | 28.44 | · +0.00 | no (±7.28) |
| K4 | grid tables | per 1k words | 0.60 | 0.60 | · +0.00 | no (±0.42) |
| | **context** | | | | | |
| C1 | output length | words | 641.44 | 641.44 | · +0.00 | no (±179.50) |
| C2 | mean paragraph length | words | 36.87 | 36.87 | · +0.00 | no (±7.75) |
| C3 | mean sentence length | words | 15.48 | 15.48 | · +0.00 | no (±1.53) |

## Substrate B  (n=60 control → n=60 treatment)

| id | metric | unit | control | this run | delta | cleared band? |
|---|---|---|---:|---:|---:|---|
| | **suppressed** | | | | | |
| S1 | one-sentence paragraphs | % of paragraphs | 31.56 | 31.56 | · +0.00 | no (±8.42) |
| S2 | long sentence then punch | % of paragraphs | 8.06 | 8.06 | · +0.00 | no (±4.57) |
| S3 | That/This pivot opener | % of sentences | 3.76 | 3.76 | · +0.00 | no (±1.76) |
| S4a | headers | per 1k words | 10.30 | 10.30 | · +0.00 | no (±2.38) |
| S4b | table rows | per 1k words | 4.20 | 4.20 | · +0.00 | no (±2.66) |
| S5 | inline bold emphasis | per 1k words | 6.81 | 6.81 | · +0.00 | no (±1.80) |
| S6 | em-dash | per 1k words | 10.75 | 10.75 | · +0.00 | no (±1.57) |
| S7 | terminal service offer | % of samples | 23.33 | 23.33 | · +0.00 | no (±15.57) |
| | **held-out** | | | | | |
| H1 | hedge density | per 1k words | 2.04 | 2.04 | · +0.00 | no (±1.05) |
| H2 | intensifier density | per 1k words | 1.87 | 1.87 | · +0.00 | no (±0.80) |
| H3 | tricolon | per 1k words | 0.57 | 0.57 | · +0.00 | no (±0.47) |
| | **collateral** | | | | | |
| K1 | list items | per 1k words | 12.78 | 12.78 | · +0.00 | no (±3.02) |
| K2 | code blocks | per 1k words | 2.23 | 2.23 | · +0.00 | no (±1.48) |
| K3 | opening paragraph | words | 27.92 | 27.92 | · +0.00 | no (±6.38) |
| K4 | grid tables | per 1k words | 0.48 | 0.48 | · +0.00 | no (±0.31) |
| | **context** | | | | | |
| C1 | output length | words | 617.87 | 617.87 | · +0.00 | no (±111.34) |
| C2 | mean paragraph length | words | 35.47 | 35.47 | · +0.00 | no (±4.87) |
| C3 | mean sentence length | words | 15.64 | 15.64 | · +0.00 | no (±1.22) |


*Band is two pooled standard errors of the difference between the arms' means. At 12 prompts there is no power for significance testing; this is effect size against measured variance.*
