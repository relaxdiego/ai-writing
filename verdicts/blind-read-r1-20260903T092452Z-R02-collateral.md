# The blind read — repeat 1

No instructions `20260903T003018Z`, under the rules `20260903T092452Z-R02-collateral`.

| question | register | picked | which arm | what made the difference |
|---|---|---|---|---|
| Bug fix report from a tool log | conversational | B | under the rules |  |
| Direct technical explanation | conversational | A | under the rules |  |
| Reporting a partially failed refactor | conversational | A | under the rules |  |
| Design tradeoff question | conversational | B | under the rules |  |
| Reporting an inconclusive investigation | conversational | A | under the rules |  |
| Responding to user pushback | conversational | A | under the rules |  |
| Explaining why a proposed approach will not work | conversational | B | under the rules |  |
| README for a small tool | document | A | under the rules |  |
| Pull request description from a diff | document | A | under the rules |  |
| Architecture decision record | document | B | under the rules |  |
| Incident postmortem | document | A | no instructions |  |
| Migration guide | document | B | under the rules |  |

**11 under the rules · 1 no instructions · 0 no difference**

---

## This read is contaminated. Do not quote the 11/12.

The copyeditor said so themselves, unprompted, after pasting the table:

> "I think I may have been biased in my answers because this isn't really the
> first time I've read those proses so the 'blind read' isn't really completely
> blind."

They are right, and the fault is the harness's, not theirs. An audit of what the
earlier galleys put in front of them:

| galley | what it showed | arms named? |
|---|---|---|
| `make_verdict_reader.py` | the opening paragraph of **every** substrate-A sample, all three repeats, both arms | **yes** — "no rules at all" / "rules as they were" / "rules with the clauses" |
| `make_paragraph_reader.py` | the 40 longest paragraphs, run and control | no |
| `make_s1_reader.py` | every one-sentence paragraph, run and control, some marked by them as the defect | no |

Share of each answer's words already seen, by union of the three galleys:

| arm | repeat 1 | repeat 2 | repeat 3 |
|---|---:|---:|---:|
| under the rules | 51% | 47% | 54% |
| no instructions | 51% | 44% | 45% |

Two things follow.

**The blinding was broken at the top of every pair.** The verdict galley labelled
the arm of every opening paragraph. The opening is the first thing read, and the
rules move it hard (K3, 28.44 -> 36.72). A reader who remembered any one of those
openings knew the arm before reaching the second paragraph.

**Rebuilding at another repeat does not fix it.** Exposure is about half at every
repeat, and the openings were labelled at every repeat. There is no clean
substrate-A text left at this style SHA.

The marks are kept because they are still the copyeditor's judgement of the
prose. They are not evidence that the rules can be felt blind.
