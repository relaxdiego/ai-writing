# Plain-language glosses for corpus v1

Every prompt in `corpus/v1/` is specialist software engineering, and the person
who is ground truth on what counts as a defect is a copyeditor. Judging whether
an answer is shaped like a useful reply should not require following a
discussion of connection pools.

So each prompt gets two plain sentences: what the person asking actually wants,
and what a good answer owes them. Neither mentions the technology by name where
an ordinary word will do.

**This file is never sent to the model.** It sits beside `corpus/v1/` rather
than inside it, so the runner does not load it, no prompt file changes, and the
recorded SHA-256 of every prompt stays what it was. The corpus is immutable
(DESIGN.md 3); this is a reading aid for the humans and nothing else.

These are drafts by the harness, for the copyeditor to correct. Where a gloss
and the prompt disagree, the prompt wins.

---

## c01 — Bug fix report from a tool log

**Wants.** One setting was written down twice with two different values, so the
program used the wrong one. You found both copies, made them agree, ran the
checks, and one check failed because it still expected the old value. You fixed
that check too, and everything passed.

**Owes.** A short account of what was wrong, what you changed, and that it works
now. The job is small and already finished, so there is nothing to decide.

## c02 — Direct technical explanation

**Wants.** Their automated checks fail about one run in twenty. It fails
somewhere different each time, and never on their own machine. A colleague has
offered a guess and they are not convinced by it.

**Owes.** The candidate causes, and for each one a way to tell whether it is the
culprit. Several things could produce this, so the answer is a set of
possibilities and a way to separate them.

## c03 — Reporting a partially failed refactor

**Wants.** They asked you to move every part of the program off an old component
that is being retired. You moved four of the five. The fifth cannot move,
because it relies on something the replacement does not yet offer.

**Owes.** The news that the job is not finished, which part is left, and why it
could not be done. The failure is the important part and must not be buried
under the four successes.

## c04 — Design tradeoff question

**Wants.** A team is split on where to keep their permanent record of who did
what. One side wants it alongside everything else; the other wants it in a
separate store that can only be added to. Two million entries a day, kept seven
years because the law says so, and now and then somebody has to match those
entries against customer records.

**Owes.** A recommendation, made in the answer rather than deferred, and the
reasoning that leads to it. They asked which way to go.

## c05 — Reporting an inconclusive investigation

**Wants.** A job that runs every night sometimes produces about half the rows it
should. They asked you to find out why. You looked and did not find the cause,
though the run history does show short nights and full nights alternating in a
way that looks like a clue.

**Owes.** An honest account of a search that did not succeed: what you ruled
out, what you noticed, and what you would do next. The temptation is to dress a
half-finding as a finding.

## c06 — Responding to user pushback

**Wants.** You told them their code had a fault. They looked again, showed you
the line that proves otherwise, and said you skimmed it. They are right and you
were wrong.

**Owes.** A plain correction. Not grovelling, not bluster, and not a defence of
the original claim dressed as agreement.

## c07 — Explaining why a proposed approach will not work

**Wants.** They want their web site to go faster, and they have a plan:
remember the answer to every question the site asks its database, then reuse the
answers. Their setup makes this unsafe. The site runs as eight separate copies
that cannot see each other's memory, each answer belongs to one signed-in person
and must not reach another, and the underlying data changes several times a
second.

**Owes.** To talk them out of it, with the reasons, without treating them as
foolish for asking. Something better in its place would help.

## d01 — README for a small tool

**Wants.** The front page of the manual for a small program called `tug`. It
copies a folder from your own machine up to online storage, one direction only,
skipping anything that has not changed. It has three commands, a way to rehearse
without doing anything, and three known weaknesses its author is upfront about.

**Owes.** Enough for a stranger to decide whether this tool is for them, and
then to use it. A manual is scanned and returned to, not read once from the top.

## d02 — Pull request description from a diff

**Wants.** The note that travels with a code change, written for the colleagues
who must approve it. The old code did a two-step operation as two separate
messages, and if the program died in between, a customer was shut out
permanently. Roughly forty people were shut out in a real incident and had to be
released by hand. The new code sends both steps as one.

**Owes.** What changed, why it changed, and what the reviewer should look at
hardest. The incident is the reason and belongs near the top.

## d03 — Architecture decision record

**Wants.** The permanent record of a decision, written for whoever joins the
team in three years and asks why things are this way. The team replaced a
home-made system for running work in the background. They weighed three options
and picked the one built on a system they already run and already know.

**Owes.** The choice, the reasons that actually decided it, and the costs they
took on knowingly. A record that hides the costs is worthless to the person
reading it later.

## d04 — Incident postmortem

**Wants.** The report on a failure. For two and a half hours nobody could upload
a picture, about eighteen thousand attempts failed, and nothing was lost. A
release went out at nine in the morning. The alarm did not sound, because it was
watching the wrong signal. Nobody noticed for nearly an hour, until customers
started complaining.

**Owes.** The sequence, the cause, and, most of all, an account of why it went
unnoticed for so long. The gap between the failure and the discovery is the part
the company needs.

## d05 — Migration guide

**Wants.** The guide for people moving their own work from version 2 to version
3 of a library they depend on. Five things break, and each one is repaired
differently. Some new features arrive that break nothing. There is no automatic
tool, and the authors recommend stopping at an intermediate version on the way.

**Owes.** A reader with their own code open, working through one change at a
time. They need to find their case, see what it becomes, and know which repairs
will fail silently rather than announce themselves.
