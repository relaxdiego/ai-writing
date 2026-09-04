# The runs

An index of what has been measured and what each run settled. Reports and raw
outputs live in each directory; this file is the only place that says why a run
exists. `DESIGN.md` is the authority on method and `TAXONOMY.md` on the defects.

Costs are the run's own `totals.cost_usd`. Substrate A alone is 36 samples and
about six minutes; substrate B is 60 samples at N=5.

| run | style sha | settles | cost |
|---|---|---|---:|
| `baseline/20260903T003018Z` | — | frozen control, corpus v1 | $6.60 |
| `runs/20260903T030500Z-R01` | `c0b903f4` | R01 retired; its stated reason was wrong | $4.24 |
| `runs/20260903T031737Z-R02` | `0f709798` | the cadence is instructable | $6.28 |
| `runs/20260903T035059Z-R03-R06` | `7695fb2e` | all eight suppressed metrics clear | $6.56 |
| `runs/20260903T040710Z-ablate-R03` | `108ae832` | R03 does nothing | $6.02 |
| `runs/20260903T042140Z-ablate-R05` | `a4d6ab4e` | S7 belongs to R05; S2 does not | $5.53 |
| `runs/20260903T092452Z-R02-collateral` | `9b16d5ae` | R02 undivided, against the old collateral set | $2.89 |
| `runs/20260903T193603Z-ablate-R02` | `72ea0582` | S1 ranks the arms backwards | $3.60 |
| `runs/20260903T200301Z-split-R07-R08-R09` | `2b62946e` | the split holds; rule order is a null | $2.80 |
| `runs/20260903T202317Z-v2-control` | — | **frozen control, corpus v2** | $2.70 |
| `runs/20260903T202854Z-v2-treatment` | `2b62946e` | the arm that passed the first real blind read | $2.60 |
| `runs/20260903T224835Z-v2-r09-flourish` | `bb3535a1` | a reworded rule does not seed its vocabulary | $2.81 |
| `runs/20260903T231128Z-R10-scan-not-length` | `daee39bf` | **R10; the length test was the wrong discriminator** | $2.99 |
| `runs/20260904T032924Z-guide-as-shipped` | `f20b1ebd` | **the released wording, measured and read at last** | $2.93 |
| `runs/20260904T040350Z-closing-sections-only` | `606d76ec` | the packager's two appended sections are inert | $3.36 |
| `runs/20260904T041718Z-ids-stripped-only` | `e29ff8a0` | stripping the rule IDs costs three em-dashes | $2.67 |
| `runs/20260904T042944Z-preamble-only` | `95352c77` | the preamble is inert too; the three interact | $2.95 |
| `runs/20260904T051132Z-R06-no-permit` | `e139dce0` | R06's permitting sentence is a foil, not a licence | $2.75 |

**18 runs, $70.28 to date.**

Style shas before 2026-09-04 name the assembler's old output, which had a
one-line header and `## Rnn` headings. From `20260904T032924Z-guide-as-shipped`
onward the injected prompt is the guide as it ships, so a style sha names the
released document itself (`DESIGN.md` 12).
