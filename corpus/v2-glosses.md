# Plain-language glosses for corpus v2

Every prompt in `corpus/v2/` is software engineering, and the person who is
ground truth on what counts as a defect is a copyeditor. Judging whether an
answer is shaped like a useful reply should not require following the subject.

So each prompt gets two plain sentences: what the person asking actually wants,
and what a good answer owes them.

**v2 chose its subjects to be readable.** v1 was uniformly specialist — connection
pools, Redis pipelines, row locking — and the copyeditor named that as a real
obstacle. v2 keeps the same twelve tasks and the same register mix, and changes
only the subject matter: dates, photographs, spreadsheets, uploaded files. The
writing task is identical; the vocabulary is not.

**This file is never sent to the model.** It sits beside `corpus/v2/` rather than
inside it, so the runner does not load it and no prompt file changes. The corpus
is immutable (DESIGN.md 3); this is a reading aid for the humans and nothing else.

These are drafts by the harness, for the copyeditor to correct. Where a gloss and
the prompt disagree, the prompt wins.

---

## c01 — Bug fix report from a tool log

**Wants.** Bookings were showing the wrong day to people in distant countries,
because the date was being read off the clock in one fixed place rather than the
clock where the booking happens. You fixed it and the checks now pass.

**Owes.** A short account of what was wrong, what you changed, and that it works
now. The job is small and already finished, so there is nothing to decide.

## c02 — Direct technical explanation

**Wants.** Photographs people upload come out sideways on the site but look right
everywhere else, always the same way for the same photograph.

**Owes.** Why this happens, and what to do about it. There is one cause and one
ordinary remedy, so the answer can be short and definite.

## c03 — Reporting a partially failed refactor

**Wants.** They asked for one word to be renamed everywhere. You renamed it in
most places, and stopped at one file where the word is part of a file format
other people's spreadsheets read, so changing it would break them.

**Owes.** What you changed, what you deliberately did not change and why, and the
one check that now fails because of it. The unfinished part is the point of the
message, not a footnote.

## c04 — Design tradeoff question

**Wants.** They keep uploaded files on one machine's disk and are about to run
three machines. They want to know whether to share the disk or move the files to
a storage service.

**Owes.** A recommendation, and the two or three things that actually decide it
at their size. They gave their size and their team, so an answer that does not
use those numbers has not answered them.

## c05 — Reporting an inconclusive investigation

**Wants.** A few people are being signed out mid-session and nobody can reproduce
it. You looked and did not find the cause, though you found a pattern in the
timing worth following.

**Owes.** What you found, plainly, and that you did not find the cause. The
finding is a lead, not an answer, and saying so is most of the job.

## c06 — Responding to user pushback

**Wants.** You advised a delay before deleting an account. They disagree, firmly,
and give reasons, including a worry about the law.

**Owes.** A straight answer to what they said. They have decided; the reply
should say which of their points you accept, correct anything genuinely wrong,
and get on with it.

## c07 — Explaining why a proposed approach will not work

**Wants.** They propose storing a copy of the search page for an hour so repeat
searches are instant. Each person sees different results, some of which they are
not allowed to see, and prices change during the day.

**Owes.** Why this breaks, concretely, and what to do instead. The serious part
is that it would show people other people's things, and that has to be
unmistakable.

## d01 — README for a small tool

**Wants.** A page introducing a tool that renames photograph files to start with
the date the photograph was taken.

**Owes.** What it is for, how to install and run it, what it does by default, and
how to undo it. Someone should be able to use it safely from this page alone.

## d02 — Pull request description from a diff

**Wants.** A description of a change that fixes an import which silently dropped
rows from customers' spreadsheets.

**Owes.** What was wrong, what the change does, and how it was checked. A
reviewer should be able to read this instead of reconstructing the story.

## d03 — Architecture decision record

**Wants.** A record of the decision to move uploaded files off local disk to a
storage service, with the alternatives and the costs.

**Owes.** The decision, the reasons that actually decided it, the options
rejected and why, and the costs being accepted knowingly. It is written for
someone who arrives in two years and asks why.

## d04 — Incident postmortem

**Wants.** An account of a nightly cleanup job that deleted 4,200 live records
because an unrelated change made live records look abandoned.

**Owes.** What happened, in time order; why it happened, including that two
reasonable changes were only dangerous together; how it was found and fixed; and
what would prevent it. Blame is not the point and should not read as though it
is.

## d05 — Migration guide

**Wants.** A guide for people upgrading a library from version 2 to version 3.

**Owes.** What must change, what changes itself, and what breaks silently. The
one change with no automatic fix is the part that matters most and should be
impossible to miss.
