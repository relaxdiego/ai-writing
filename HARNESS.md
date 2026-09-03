# Running the evals

How the harness is operated, and what its numbers can and cannot say. `DESIGN.md`
is the decision record and the authority; where the two disagree, `DESIGN.md` is
right and this file is stale, while `CLAUDE.md` carries the writing rules
themselves.

Nothing here is a current result. Results live in `runs/<utc>-<label>/report.md`,
the attribution lives in `style/rules.md`, and the ratified defects live in
`TAXONOMY.md`.

## Money

Runs cost real money and the user pays, so propose the spend and let them decide.
There is no CI, because headless auth is unavailable on push and threshold gating
would fail routine commits. Every run is a deliberate purchase.

As measured on Opus with a twelve-prompt corpus: a 96-sample run across both
substrates costs $4 to $7 and takes twelve to fourteen minutes; substrate A alone
at three repeats is about $3 and six minutes; the pairwise judge is about $1.60.
Each manifest records exact token counts and cost, so treat these as the shape of
the bill rather than the bill.

## The commands

    python3 harness/assemble.py                      # -> build/style.prompt.md
    python3 harness/assemble.py --ablate R10 --out /abs/path/build/style.x.md

    nohup python3 harness/run.py --arm treatment \
      --style /abs/path/build/style.prompt.md --corpus vN --substrates a \
      --runs-a 3 --out /abs/path/runs/$(date -u +%Y%m%dT%H%M%SZ)-LABEL \
      --label "what this run is for" > /abs/path/.scratch/run.log 2>&1 &

    python3 harness/score.py <abs-run-dir> --against <abs-baseline> --rules <ids>
    python3 harness/judge.py <abs-run-dir> --against <abs-control>

Every path passed to the CLI must be absolute.

Score twice. Against the frozen control for the absolute effect, which is what
acceptance is measured on, and against the previous run for the marginal effect,
which is what attribution is argued from. Each corpus version has its own frozen
control and the versions are not comparable as absolute numbers.

The `--rules` label is what a report claims the run contained, so re-scoring a
historical run needs the label that run actually shipped. Read it out of the run's
own `report.md` header rather than reconstructing it from memory.

The galley builders are `make_plain_reader.py` for a blind read, and
`make_verdict_reader.py`, `make_s1_reader.py` and `make_paragraph_reader.py` for
labelled lab reads. Publish a galley as an Artifact and give the user the link.

## Rules and their IDs

A rule ID is an address, not a rank. It records when the rule was written, and the
assembler emits rules in file order, which is the order the model reads them in.
Where a rule sits is part of the treatment, so moving a rule is a change and needs
its own run to isolate it from the edit that prompted the move.

An ID is never reused and never assembled once retired, so every historical
`--rules` label still names the exact text that ran. There are three ways a rule
leaves and the retirement note has to say which: **withdrawn**, when the rule did
not do what it claimed; **divided**, when the text had become more than one
instruction; **replaced**, when the instruction now says something different. A
material change to what a rule says takes a new ID, and fixing a typo does not.

A rule stays only where a run isolates its effect, never because the stack it sits
in cleared. Where the evidence is inherited or borrowed, the attribution table
says "claimed, not earned", and the phrase is not decoration.

Stack first, then ablate the doubtful. Routine full ablation is rules times
prompts times repeats and is a bad trade at these prices. Two rules have been
found to be doing nothing, or not the thing they were credited with, and both were
found by ablating one rule after the stack had already cleared.

Rules must never name a held-out mannerism. The held-out set guards against the
rules dodging named tokens instead of changing how the model writes, and naming
one destroys it.

## What the numbers can and cannot say

Detectors report normalized rates per 1,000 words, as a vector with no composite
headline score. Collapsing distinct tics into one number hides fixing two while
worsening three.

The noise band is twice the pooled standard error of the difference between the
arms' means, built from within-prompt variance only. Both arms answer the same
frozen prompts, so a prompt that simply draws longer answers raises both means and
cancels. Taking the spread across all samples folds that between-prompt variation
into the noise term and inflates every band, on some metrics threefold. A change
counts when it moves a metric outside its band. At twelve prompts there is no
power for significance testing, and a p-value would imply rigor the sample size
cannot support.

One metric in twenty clearing a two-sigma band is what chance alone produces, so a
single clearing metric in a full scorecard is not a finding.

Cadence detectors rank above markup detectors. The prose is tiring to read because
of its paragraph cadence, not because of its em-dashes. Markup rates are real and
secondary, and must never stand in for the cadence measures.

**Never read "cleared" as "fixed" on a K row.** The K metrics are collateral:
structure the rules must not destroy. A K metric below the control is a loss that
the scorecard reports as a number going down.

**A suppressed metric at zero is not always a win.** Zero tables reads as a clean
scorecard and can mean the rules removed a table the reader wanted.

**Say which estimator produced a figure.** Every estimator fault found so far
changed a published reading, and `TAXONOMY.md` records each one against the entry
it belongs to. Two were the same fault: a suppressed metric and a collateral
metric counting the same markup, so the rules restoring structure read on the
scorecard as a defect returning. Check for that pairing before believing any
suppressed metric that moves the wrong way. A figure without its estimator named
is not a figure.

Adding a detector or changing an estimator invalidates every cached `result.json`,
so delete them all and re-score, which costs nothing.

A detector that cannot see a paragraph's neighbours will misread it. `Doc` carries
`.blocks` for exactly that.

Every detector must be justified against a quoted passage from a real sample and
never invented a priori. Detector selection is itself a bias, and the first pass
at the taxonomy measured markup because markup is easy to regex, while the
paragraph cadence sailed through unmeasured.

An instruction does not seed its own vocabulary into the output. Changing one word
in a rule and re-running tested it, and the replacement word appeared zero times
while the original word did not fall. A word appearing more often under
instruction is not evidence that the instruction named it. The same run is the
closest thing to a null result the project has, because a one-word prompt edit
cleared zero of twenty bands.

## The blind read

The gate is a person reading both arms' answers whole, with no numbers on the
page, columns assigned from a hash of the sample key, and the arm revealed per
pair only after the verdict. "No difference" is a first-class answer and it is the
one the measurements cannot give. Detectors and the judge both work on fragments
or aggregates, and a person cannot feel a prose change from pieces the size of a
detector.

**A reader's naivety about a sample is a consumable resource and looking spends
it.** It cannot be restored and it is not visible in any run directory. The first
blind read was spent before it happened, because a labelled lab galley had already
shown the opening paragraph of every substrate-A sample under explicit arm labels,
and nothing in the harness knew.

`harness/exposure.py` is the ledger and it is committed, because it is evidence
about the reader rather than about the model. Every galley records the sample keys
it showed and whether it named the arm. Two things follow: do not point a lab
galley at a run reserved for reading, and generate more repeats than a galley will
show so the remainder stays clean.

`make_plain_reader.py` warns over already-shown text and does not refuse, so read
the warning.

Read a generated galley in full before publishing it. Its intro has been wrong
twice, and only reading the whole file caught it.

Do not rebuild a galley's URL from a filed verdict while other people are still
reading it. The builder bakes a filed verdict into the page as a seed, so every
pair the first reader marked would arrive pre-marked and revealed, and a seeded
copy has to go out as a separate artifact instead.

Verdicts stay in each reader's own browser and reach nobody until the reader
presses Copy verdict and sends the table on. Collection is manual, and each
returned table is filed under `verdicts/`.

## Reader-facing copy

Use a cold subagent for anything a stranger will read. Two passes written from
inside the project left project vocabulary in reader-facing copy both times. The
agent that got it right was given one file, a plain brief and a ban list, and told
to read nothing else. Somebody who knows the jargon has to remember not to use it,
and forgets.

## The clean room

A scratch `CLAUDE_CONFIG_DIR` is synthesized per run with `.credentials.json`
copied in at mode 600 and removed by an exit trap. The scratch directory is
required and not stylistic: `--bare` and a bare redirected config dir both fail
subscription auth on this CLI. If an `ANTHROPIC_API_KEY` ever appears, switch to
`--bare`, which is the stricter room, and remember that the judge runs in the same
room as the samples.

Manifests record a summarized inventory of the config directory deliberately, so
keep it summarized. `run.py` redacts local absolute paths from the manifest argv.

## Traps that have already cost time

- **Never pipe `run.py` to `head`.** It killed a whole run mid-flight.
- **`pgrep -f "harness/run.py"` matches its own watcher.** Use
  `pgrep -f "^python3 harness/run.py"`.
- **Verify a run finished** by checking for `<run-dir>/manifest.json`, then check
  `totals.failed` in it. A killed run still writes a manifest.
- **Do not put anything inside `corpus/vN/`.** The runner globs it. Glosses live
  beside, at `corpus/vN-glosses.md`.
- **The corpus is immutable.** New prompts make a new version. A mutated corpus
  silently invalidates every historical comparison.
- **Read a new corpus back before spending on it.** Three fixture faults were
  caught only by reading the prompts after a run had already started.
- Raw outputs are kept forever, plain text, never compressed, so a detector
  written later can be backfilled across all history.
