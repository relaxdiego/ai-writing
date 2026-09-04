# Running the evals

How the harness is operated, and what its numbers can and cannot say. `DESIGN.md`
is the decision record and the authority; where the two disagree, `DESIGN.md` is
right and this file is stale.

**This repo has no `CLAUDE.md` and must not get one.** The packaged style guide
is the project's deliverable, and it is written outside the repo:

    python3 harness/package_style.py     # -> ~/.claude/CLAUDE.md

The packager takes the rule text verbatim from `style/rules.md`, strips the IDs,
adds two closing sections, and refuses to emit a guide that names a rule ID, a
run, a metric, a corpus, a substrate or a measurement. It also refuses any path
inside the repo, for two reasons. A second copy is a second thing to drift, and a
`CLAUDE.md` at the repo root sits in the memory-discovery chain of every
clean-room sample.

**The packager is also what the harness injects.** `package_style.build` is the
only place the wording is assembled, `assemble.py` calls it, and `run.py --guide`
builds it in process, so the document measured is the document installed. It was
not always so: the release once carried 244 words no run had seen, and those
words together with the stripped headings and the rewritten preamble interacted
to give back a quarter of the em-dash win while each was inert alone.

**Never let a memory file reach a sample.** Two mechanisms stop it and each
covers a different file. User memory follows `CLAUDE_CONFIG_DIR`, and the
synthesized scratch dir holds only credentials, so the style guide installed at
`~/.claude/CLAUDE.md` has no route in. `--setting-sources ""` in `cleanroom.sh`
covers the other file: a `CLAUDE.md` at the repo root, which every sample's cwd
sits under. Neither is redundant. A sample that read either would put the
treatment into the control arm and every comparison would be worthless while
still looking healthy.

`run.py` refuses to start if the flag has gone, but that check is a string search
over `cleanroom.sh` and not a proof that the flag still does what it did.
`harness/check_cleanroom.py --live` is the only thing that could prove it and it
currently proves nothing: it plants its canary in the real `~/.claude/CLAUDE.md`,
which the redirect has already made unreadable, so both its arms come back silent
and its own positive control refuses the result. Read its docstring for the
measured table before trusting anything here.

Nothing here is a current result. Results live in `runs/<utc>-<label>/report.md`,
what each run settled is indexed in `runs/README.md`, the attribution lives in
`style/rules.md`, the ratified defects and their rulings live in `TAXONOMY.md`,
the copyeditor's rulings in full live in `verdicts/`, and what is still open
lives in the GitHub issues.

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
    python3 harness/rescore_all.py --metric S6    # after a detector changes

An acceptance run takes `--guide` instead of `--style`. It builds the guide from
`style/rules.md` in process rather than reading `build/`, so a stale file cannot
be injected and the arm measures what ships. Keep `--style` for ablation arms,
where `assemble.py --ablate` writes the shipped document minus one rule.

`rescore_all.py` re-scores every run and rebuilds every report against the
baseline named in that report's own header, so no report quietly changes what it
compares. Three detector faults have needed it so far.

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
keep it summarized. It is also evidence rather than decoration: user memory is
read from the config dir, so an inventory with no `CLAUDE.md` in it is the proof
that no run was contaminated by the installed guide. `run.py` redacts local
absolute paths from the manifest argv.

## Working here

`DESIGN.md`, this file and `TAXONOMY.md` carry the method. These are the parts
about the person rather than the harness.

- **The copyeditor is the ground truth on what counts as a defect.** Hand over
  raw samples, whole. They have settled S5, R10's overshoot and K5's removal,
  each in one message.
- **When they say "show me", give it to them where they are.** Publish the galley
  as an Artifact and hand over the link rather than filling the terminal.
- **Give them a name to reject, not a name to accept.** A recommendation with its
  cost stated beats a survey of options.
- **Replies in ASD-STE100 Simplified Technical English.** Prose, not code.
- **Do not push without being told.** Commit locally and wait for the word.
- **Do not poll a running job at the user.** Answer the question they asked.
- **A prediction goes on the record before the run, not after.** Two predictions
  have been wrong so far and both were worth more than the runs that confirmed
  something.

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
- **Score the project's own documents with the project's own detectors.** Three
  detector faults came out of doing it, all free, and one corrected a published
  claim.
- **Count blocks per prompt, not per arm.** R04's fault was invisible in every
  aggregate and obvious in one table of twelve rows.
- **A suppressed metric and a collateral metric can count the same markup**, so a
  rule restoring structure reads as a defect returning. S4b, S5 and S6 have all
  done it. Check for the pairing before believing a metric that moves the wrong
  way.
- **The CLI is not pinned by anything but a `PATH` symlink.** Every run to date
  is 2.1.259. Check `claude --version` against the frozen control's manifest
  before spending.
