# How to write here

The writing rules below are the ones the evals have earned. Follow them in this
repository, and in prose written for a reader anywhere else.

The rules below are copied verbatim from `style/rules.md`, which is the source of
record and carries the evidence, the attribution and the retired IDs beside each
one, so when a rule changes there it has to be copied here as well.
`harness/assemble.py` emits the same text into `build/style.prompt.md`, which is
what a run injects.

A rule ID is an address, never a rank. The order below is the order the rules are
read in, and it is part of what is being tested. Retired IDs are never reused, so
R01, R02, R03 and R04 will not reappear.

## R07 — Let a paragraph develop

Carry a thought from claim through reasoning to consequence inside a single
paragraph. A paragraph holding one sentence has usually been cut away from the
one before it; join them unless the isolation is doing real work.

An answer that reaches a recommendation, a refusal, or a warning states it first
and by itself, then develops the reasoning behind it. That opening line is not a
paragraph cut away from the one after it, and it is the clearest case of the
isolation doing real work. Where the reader has to act on a danger or choose
between costs, the danger and the cost go in front of the explanation, not after
it.

## R08 — A list, a worked example and a table are not paragraphs

The instruction to develop a paragraph applies to prose only. A list is not a
paragraph that somebody chopped up. Where the content is a set of parallel
items, such as competing explanations, ordered steps, or options to choose
between, set it as a list and leave it as a list. A worked example is the same
case: a code block is the example itself, and absorbing it into the sentences
around it removes the thing the reader came for.

A table is not a paragraph either. Where several things are compared across the
same dimensions, and a reader will want to find one cell, set it as a table and
leave it as one. A timeline, a flag reference, and a before-and-after matrix are
all this case.

## R09 — Do not perform a point you have already made

Do not close a paragraph with a short verdict following a long explanation. That
shape performs insight rather than delivering it, and the explanation has
already carried the point. For the same reason, do not open a sentence with
"That is", "That's", "This means" or "It's" as a pivot into a restatement of
what you have just said.

## R10 — Reserve structure for what a reader will scan

Headings and tables are for writing a reader will scan, search and return to.
What settles that is the use, not the length. A pull request description or a
release note is read by somebody looking for one part of it, so it stays
sectioned however short it runs. A reply inside a conversation is read once,
from the top, however long it runs, and carries its organisation in the prose: a
sentence saying what you are about to take up does the work the heading was
standing in for, and it does it without breaking the page into administered
sections.

Use a table when the content is already a grid: several things compared across
the same dimensions, or figures a reader will want to read off one at a time.
Counts and timings taken out of a log or a benchmark are that case, and running
them into a sentence leaves the reader rebuilding a grid you already had. Two or
three points belong in sentences. A column of labels beside a column of prose is
a list wearing a table's clothes.

## R05 — Stop when the answer stops

Do not close by offering further work. "Want me to run these?" and "If you tell
me your test runner, I can write it" hand the reader an administrative decision
at the moment they should be reading your conclusion, and they make the answer
sound like a service counter. When something is missing that only the reader can
supply, say so where it becomes relevant in the body of the answer, then finish
on the answer itself.

## R06 — Punctuate with punctuation, emphasise with words

Reach for a comma, a colon, a semicolon or a full stop before an em-dash. The
em-dash is right where a sentence is interrupted and then resumed. It is wrong
as a general joint between two clauses, which is the use that turns it into a
tic: a colon will set the second clause in order, or a full stop will let it
stand on its own.

Do not set words in bold inside a sentence to mark stress. Bold is a structural
signal, used for a defined term or a label at the head of an entry, not a way to
raise your voice mid-clause. Where a phrase needs weight, put it where the
sentence already puts its weight, at the end of the clause.

## What the rules cost

Every rule above suppresses something. The one cost a person has priced, in a
blind read of whole answers, is structure.

**Better prose can lose to worse prose that is easier to scan.** A reader
preferred the ruled version of a pull request description and still chose the
other one, because a pull request has to be scannable, which is a finding about
the rules rather than about the reader.

So when the two pull against each other, the reader's use of the page wins. R10
carries that as a rule, and R08 protects the list, the worked example and the
table that R07 would otherwise absorb into prose. Read those two as the
counterweight to the rest, not as exceptions to it.

The cost also runs the other way. Turning a list into a table is not free either.
A set of parallel items is a list. A grid is a table. Reaching for a table
because a table is allowed produces a grid with one real dimension, and a
checklist a reader works through with a finger on the page is not improved by
becoming a matrix.

## Words and habits a reader has caught

Not rules, and no detector counts them. Each is something a copyeditor marked
while judging something else, and each is worth a second look in your own draft.

**"shape".** Caught twice, unprompted, in one sitting: "Three things change shape
once the delete is real." The noun is the tic, and the verb is usually fine.

**A negation where a plain statement would do.** "These are known and current,
not edge cases you are unlikely to reach" makes the reader resolve two negations
to arrive at "you will hit these". R07 asks for a verdict stated plainly, and a
doubled negation is how a plain verdict stops being plain.

**A qualifier that repeats the word it qualifies.** "The costs we are accepting,
and accepting knowingly." The repetition performs care instead of adding
anything.

## Where the rest of the project is

`DESIGN.md` is the decision record and the authority on how anything is measured.
`TAXONOMY.md` is the ratified list of defects, with the quoted evidence for each.
`style/rules.md` holds these rules with their attribution and the retired IDs.
`HARNESS.md` is how to run the evals, and what the numbers can and cannot say.

The user is a copyeditor and is the ground truth on what counts as a defect in
prose. Hand them raw samples, whole. Write replies in ASD-STE100 Simplified
Technical English: short sentences, active voice, ordinary words, one idea per
sentence.
