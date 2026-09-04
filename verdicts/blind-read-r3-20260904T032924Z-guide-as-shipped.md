# The blind read — repeat 3

No instructions `20260903T202317Z-v2-control`, under the rules
`20260904T032924Z-guide-as-shipped`.

Corpus v2, substrate A, repeat 3, with `d01` taken from repeat 2 because the
ledger had `d01-r3` recorded as quoted in a terminal with the arm named. Twelve
pairs, whole answers, column assigned by a hash of the sample key, arm revealed
per pair only after the verdict.

**This is the first read of the artifact that ships.** Every earlier read was of
the assembled prompt, which the runs of 2026-09-04 established is not the
released document: same six rule bodies, a different preamble, ID-free headings
and two appended sections, and those three differences interact.

| question | kind | picked | which version | what made the difference |
|---|---|---|---|---|
| Bug fix report from a tool log | conversational | A | no instructions |  |
| Direct technical explanation | conversational | A | under the rules |  |
| Reporting a partially failed refactor | conversational | B | under the rules |  |
| Design tradeoff question | conversational | B | under the rules |  |
| Reporting an inconclusive investigation | conversational | A | under the rules |  |
| Responding to user pushback | conversational | B | under the rules |  |
| Explaining why a proposed approach will not work | conversational | A | under the rules |  |
| README for a small tool | document | B | under the rules |  |
| Pull request description from a diff | document | A | under the rules |  |
| Architecture decision record | document | A | under the rules |  |
| Incident postmortem | document | A | under the rules |  |
| Migration guide | document | B | under the rules |  |

**11 under the rules · 1 no instructions · 0 no difference**

## The release passes its own gate

Eleven of twelve, no ties. Treating the twelve prompts as independent and one
reader as the instrument, a coin lands eleven or better 13 times in 4096, about
0.3%. The previous v2 read, of the R04 arm at repeat 1, went ten to two.

**The em-dash regression is below the reader's threshold.** The released wording
writes 31 forbidden joints across the whole run where the assembled prompt writes
1, which was the finding that made this read worth taking. Across these twelve
pairs it is 8 joints against the control's 53. No note mentions an em-dash. That
matters because this reader has complained about em-dashes unprompted before, on
`d02` in the repeat 1 read, where the offending arm was the control.

## No structural complaint survived R10

The repeat 1 read left four notes and every one of them faulted the ruled arm for
missing structure: no headings on `c04`, prose where a table belonged on `c05`,
a lost verdict on `d02` because headings and bullets beat better prose. That arm
carried R04. This arm carries R10, and the block counts across the twelve pairs
have moved with it:

| | ruled | control | repeat 1, ruled | repeat 1, control |
|---|---:|---:|---:|---:|
| headings | 34 | 51 | 26 | 42 |
| list items | 34 | 69 | 10 | 18 |
| table rows | 32 | 48 | 2 | 5 |
| code blocks | 11 | 16 | 10 | 20 |

The ruled arm now carries about two thirds of the control's structure where it
carried about half, and the tables are near parity. No note was left on any pair
this time. Absence of notes is weaker evidence than a note, and it is consistent
with the complaint R04 earned having been answered.

## `c01` has now lost twice

The bug fix report is the only loss here and it was also a loss in the repeat 1
read, against a different ruled arm and a different repeat. On corpus v1 it went
the other way, in the read that turned out to be spoiled.

Neither arm has structure to argue about: the ruled answer is 141 words against
the control's 170, the shortest pair in the galley by a wide margin, and it was
already noted in repeat 1 as the only pair where the ruled arm lost on prose
alone. Two independent blind reads now agree on it. That is the standing
weakness and it is a short conversational report, which is the register the whole
project is aimed at.

## What this does not settle

The read compares the release against no instructions. It does not compare the
release against the assembled prompt that was tested, so it says the shipped
wording clears the gate and not that it clears it as well as the tested wording
would. That comparison would need its own galley and would spend more of the
reader's naivety on a null that both arms are likely to produce.

One reader. Repeats 1 and 2 of `20260904T032924Z-guide-as-shipped` are unspent
apart from `c02-r2` and `d01-r2`.
