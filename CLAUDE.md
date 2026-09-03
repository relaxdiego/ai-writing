# Working in this repository

This project writes instructions that suppress AI mannerisms in Claude Code's
prose, and proves the effect with measurements instead of impressions. The
treatment is a numbered rule file. Everything else is pinned, and every claim
has to survive a run.

This file tells you how to work here. It does not restate the reasoning.
`DESIGN.md` is the decision record and the authority; read it before you change
anything about how measurement works. `TAXONOMY.md` is the ratified list of
defects, and every detector implements an entry in it. `style/rules.md` is the
shipped rule set together with the evidence for each rule and the record of the
retired ones. Where this file and `DESIGN.md` disagree, `DESIGN.md` wins and
this file is wrong.

The CLAUDE.md the project is trying to produce is a different file. `DESIGN.md`
12 keeps that one deferred until the evals say the rules are worth shipping, and
`build/style.prompt.md` is the escape hatch meanwhile.

## The person you are working with

The user is a copyeditor, and on what counts as a defect in prose they are the
ground truth and you are not. Hand them raw samples, whole, first word to last.
A detector-sized fragment cannot be judged, and a summary of a sample is your
reading substituted for theirs.

Write replies in ASD-STE100 Simplified Technical English. Short sentences,
active voice, ordinary words, one idea per sentence. Reply in prose. Commit
messages and code are exempt.

Do not let the metric lead the reading. Every time the copyeditor has been shown
text in place, the metric that sent them there turned out to be counting
something else. Show them the text and let them say what is wrong with it.

Give them a name to reject rather than a name to accept. A proposed taxonomy
entry, a proposed rule, a proposed retirement: put it in front of them already
written, so the work is judging it and not inventing it.

Use a cold subagent for anything a stranger will read. The galley intro proved
this. Two passes written from inside the project left project vocabulary in
reader-facing copy both times. The agent that got it right was given one file, a
plain brief and a ban list, and told to read nothing else. Somebody who knows the
jargon has to remember not to use it, and forgets.

Do not poll a running job at the user. Answer the question they asked.

## Money

Runs cost real money and the user pays. Propose the spend and let them decide.

    a 96-sample run, both substrates          $4-7, 12-14 min
    substrate A alone, 36 samples             $2.60-3.60, about 6 min
    the pairwise judge                        about $1.60
    a single-rule ablation on substrate A     about $3

Spend to date is recorded in the handoff and in each run's manifest, which
carries exact token counts and cost. There is no CI, because headless auth is
unavailable on push and threshold gating would fail routine commits, so every
run is a deliberate purchase.

## How to run it

    python3 harness/assemble.py                      # -> build/style.prompt.md
    python3 harness/assemble.py --ablate R10 --out /abs/path/build/style.x.md

    nohup python3 harness/run.py --arm treatment \
      --style /abs/path/build/style.prompt.md --corpus v2 --substrates a \
      --runs-a 3 --out /abs/path/runs/$(date -u +%Y%m%dT%H%M%SZ)-LABEL \
      --label "what this run is for" > /abs/path/.scratch/run.log 2>&1 &

    python3 harness/score.py <abs-run-dir> \
      --against /abs/path/runs/20260903T202317Z-v2-control \
      --rules R07,R08,R09,R10,R05,R06
    python3 harness/judge.py <abs-run-dir> --against <abs-control>

Every path passed to the CLI must be absolute.

Score twice. Against the frozen control for the absolute effect, which is what
acceptance is measured on, and against the previous run for the marginal effect,
which is what attribution is argued from. Corpus v1 and v2 are not comparable as
absolute numbers and each has its own frozen control.

Re-scoring a historical run needs its own `--rules` label, because the label is
what the report claims the run contained. In run order the labels are: R01; R02;
R02,R03,R04,R05,R06; R02,R04,R05,R06; R02,R04,R06; R02,R04,R05,R06; R04,R05,R06;
R07,R08,R09,R04,R05,R06 from the split onward; and R07,R08,R09,R10,R05,R06 from
the R04 replacement onward.

The galley builders are `make_plain_reader.py` for a blind read,
`make_verdict_reader.py`, `make_s1_reader.py` and `make_paragraph_reader.py` for
labelled lab reads. Publish a galley as an Artifact and give the user the link.

## Rules and their IDs

A rule ID is an address, not a rank. It records when the rule was written, and
the assembler emits rules in file order, which is the order the model reads them
in. Where a rule sits is part of the treatment, so moving a rule is a change and
needs its own run to isolate it from the edit that prompted the move.

An ID is never reused and never assembled once retired, so that every historical
`--rules` label still names the exact text that ran. There are three ways a rule
leaves, and the retirement note has to say which. R01 and R03 were withdrawn,
because they did not do what they claimed. R02 was divided into R07, R08 and
R09, because the text had become more than one instruction. R04 was replaced by
R10, because the instruction now says something different. A material change to
what a rule says takes a new ID, and fixing a typo does not.

A rule stays only where a run isolates its effect, never because the stack it
sits in cleared. Where the evidence is inherited or borrowed, the attribution
table says "claimed, not earned", and the phrase is not decoration: R09 and R10
both carry it now.

Stack first, then ablate the doubtful. Routine full ablation is rules times
prompts times repeats and is a bad trade at these prices. R03 turned out to do
nothing and R02 turned out not to do what it was credited with, and both were
found by ablating one rule after the stack had already cleared.

Rules must never name a held-out mannerism. The held-out set is the guard
against the rules dodging named tokens instead of changing how the model writes,
and naming one destroys it.

## What the numbers can and cannot say

Detectors report normalized rates per 1,000 words, as a vector with no composite
headline score. Collapsing eight tics into one number hides fixing two while
worsening three.

The noise band is twice the pooled standard error of the difference between the
two arms' means, built from within-prompt variance only. Both arms run the same
frozen prompts, so a prompt that simply draws longer answers raises both means
and cancels. Taking the spread across all 36 samples folds that between-prompt
variation into the noise term and inflates every band, on some metrics
threefold. A change counts when it moves a metric outside its band. There is no
power for significance testing at twelve prompts and a p-value would imply rigor
the sample size cannot support.

One metric in twenty clearing a two-sigma band is what chance alone produces, so
a single clearing metric in a full scorecard is not a finding.

Cadence detectors rank above markup detectors. The prose is tiring to read
because of S1 and S2, not because of em-dashes. Markup rates are real and
secondary, and must never stand in for the cadence measures.

**Never read "cleared" as "fixed" on a K row.** The K metrics are collateral:
structure the rules must not destroy. A K metric below the control is a loss the
scorecard reports as a number going down. K1, K2 and K4 are all still below the
control, and the first blind read confirmed that with a person.

**A suppressed metric at zero is not always a win.** S4b proved it and the R02
ablation proved it again. Zero tables reads as a clean scorecard and can mean the
rules removed a table the reader wanted.

**Say which estimator produced a figure.** Four estimator faults have been found
so far, and each one changed a published reading. S2 averaged a per-sample
percentage, so a three-paragraph reply weighed as much as a thirty-paragraph
document. S4b counted rows in a way that turned a total loss into a success. S1
has two estimators still in circulation, one averaging a capped per-sample
percentage and one pooled and uncapped, reading 29.84 and 35.55 on the same
control. S5 counted a bold label opening a list item, which R06 permits, so a
metric reported as a defect returning was measuring R08 restoring lists; the
copyeditor ruled on it, the detector was fixed and every run re-scored. A figure
without its estimator named is not a figure.

Two of those four are the same fault: a suppressed metric and a collateral
metric counting the same markup. When the rules restore structure the suppressed
metric rises, and the scorecard reports a win as a regression. Check for that
pairing before believing any suppressed metric that moves in the wrong
direction.

Adding a detector or changing an estimator invalidates every cached
`result.json`, so delete them all and re-score, which costs nothing.

A detector that cannot see a paragraph's neighbours will misread it. `Doc`
carries `.blocks` for exactly this reason. S1 counts an opening verdict and a
list lead-in as defects because it cannot see what follows them.

Every detector must be justified against a quoted passage from a real sample and
never invented a priori. Detector selection is itself a bias, and the first pass
at the taxonomy measured markup because markup is easy to regex while the
staccato sailed through unmeasured.

An instruction does not seed its own vocabulary into the output. Changing one
word in R09 and re-running tested it, and the replacement word appeared zero
times while the original word did not fall. A word appearing more often under
instruction is not evidence that the instruction named it. The same run is the
closest thing to a null result the project has, because a one-word prompt edit
cleared zero of twenty bands.

## The blind read

The gate is a person reading both arms' answers whole, with no numbers on the
page, columns assigned from a hash of the sample key and the arm revealed per
pair only after the verdict. "No difference" is a first-class answer and it is
the one the measurements cannot give. Detectors and the judge both work on
fragments or aggregates, and a person cannot feel a prose change from pieces the
size of a detector.

**A reader's naivety about a sample is a consumable resource and looking spends
it.** It cannot be restored and it is not visible in any run directory. The
first blind read was spent before it happened, because a labelled lab galley had
already shown the opening paragraph of every substrate-A sample under explicit
arm labels, and nothing in the harness knew.

`harness/exposure.py` is the ledger and it is committed, because it is evidence
about the reader rather than about the model. Every galley records the sample
keys it showed and whether it named the arm. Two consequences follow. Do not
point a lab galley at a run reserved for reading, and generate more repeats than
a galley will show so the remainder stays clean.

`make_plain_reader.py` warns over already-shown text. It does not refuse. Read
the warning.

Read a generated galley in full before publishing it. The intro was wrong twice
and only reading the whole file caught it.

Do not rebuild a galley's URL from a filed verdict while other people are still
reading it. The builder bakes a filed verdict into the page as a seed, so every
pair the first reader marked would arrive pre-marked and revealed, so publish a
seeded copy as a separate artifact instead.

Verdicts stay in each reader's own browser and reach nobody until the reader
presses Copy verdict and sends the table on. Collection is manual, and each
returned table is filed under `verdicts/`.

## The clean room

A scratch `CLAUDE_CONFIG_DIR` is synthesized per run with `.credentials.json`
copied in at mode 600 and removed by an exit trap. The scratch directory is
required and not stylistic: `--bare` and a bare redirected config dir both fail
subscription auth on this CLI. If an `ANTHROPIC_API_KEY` ever appears, switch to
`--bare`, which is the stricter room, and remember that the judge runs in the
same room as the samples.

Manifests record a summarized inventory of the config directory deliberately.
Keep it summarized. `run.py` redacts local absolute paths from the manifest's
argv.

## Traps that have already cost time

- **Never pipe `run.py` to `head`.** It killed a whole run mid-flight.
- **`pgrep -f "harness/run.py"` matches its own watcher.** Use
  `pgrep -f "^python3 harness/run.py"`.
- **Verify a run finished** by checking for `<run-dir>/manifest.json`, then check
  `totals.failed` in it. A killed run still writes a manifest.
- **Do not put anything inside `corpus/v1/` or `corpus/v2/`.** The runner globs
  them. Glosses live beside, at `corpus/vN-glosses.md`.
- **The corpus is immutable.** New prompts make a new version. A mutated corpus
  silently invalidates every historical comparison.
- **Read a new corpus back before spending on it.** Three fixture faults were
  caught only by reading the prompts after a run had already started.
- Raw outputs are kept forever, plain text, never compressed, so a detector
  written later can be backfilled across all history.

## Where the work stands

The shipped set is R07, R08, R09, R10, R05, R06, in that file order. The first
genuinely blind read gave ten of twelve to the rules with no ties, on corpus v2
text the reader had never met.

Every complaint in that read was the same complaint: the ruled arm has less
structure. R10 answers the part of it that R04 caused. Its run restores the
headings to the pull request description and the table to the inconclusive
investigation, keeps conversational headings at zero, and overshoots on tables,
which now sit above the control while list items fall further below it. Whether
that trade reads as an improvement is the copyeditor's call and is open.

The open items are listed in the handoff at `~/handoff/ai-writing-handoff.md`.
The live ones are the R07, R08 and R09 ablations, the choice of S1 estimator,
"shape" as a taxonomy candidate, entry 8's thirteen unmarked labels, and S7's
kind disagreeing between `TAXONOMY.md` and `detectors.py`.
