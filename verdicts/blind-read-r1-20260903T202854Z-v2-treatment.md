# The blind read — repeat 1

No instructions `20260903T202317Z-v2-control`, under the rules `20260903T202854Z-v2-treatment`.

Corpus v2, substrate A, repeat 1. Twelve pairs, whole answers, column assigned by
a hash of the sample key, arm revealed per pair only after the verdict. The
exposure ledger was clean for both runs: no galley had shown any of this text
before, so this is the first blind read in the project that was actually blind.

| question | kind | picked | which version | what made the difference |
|---|---|---|---|---|
| Bug fix report from a tool log | conversational | A | no instructions |  |
| Direct technical explanation | conversational | A | under the rules |  |
| Reporting a partially failed refactor | conversational | A | under the rules |  |
| Design tradeoff question | conversational | B | under the rules | Unfortunately though, B's scannability is reduced due to total lack of headings. Additionally, in B, this reads wierd to me: "The shared-disk option is the one that looks like less work and isn't. " particularly the "and isn't" part. I would write that as "but isn't" or use something other than an "and" phrase. |
| Reporting an inconclusive investigation | conversational | A | under the rules | A caveat: A's readability is reduced by relying exclusively on prose when a table could've made things clearer. Example is its second paragraph. |
| Responding to user pushback | conversational | A | under the rules | The word "shape" is overused though. In fact, "Three things change shape once the delete is real" really sounds off to me. I would've written it as "There are three things that will influence how this will be implemented:" |
| Explaining why a proposed approach will not work | conversational | B | under the rules | "you may be holding the quote." is an unfamiliar idiom for me. |
| README for a small tool | document | A | under the rules | B has the extra "Here's the README. I've kept it to what you specified..." and is immediately followed by the 3-backtick delimiter which ruined the formatting of the README body. |
| Pull request description from a diff | document | B | no instructions | I actually like the prose in A better but B is more scannable because of the headings and bullets, and in the context of reading PRs, scannability is important. I do dislike the overuse of em dashes  in B though. A minor thing in A is that it uses the overused "shape." |
| Architecture decision record | document | B | under the rules |  |
| Incident postmortem | document | B | under the rules | A reads better in some parts though: because of the "Impact" bulleted list and its Action Items presented as a table. |
| Migration guide | document | B | under the rules |  |

**10 under the rules · 2 no instructions · 0 no difference**

## What the verdict says

Ten of twelve to the rules, two against, no ties. Treating the twelve prompts as
independent and one reader as the instrument, a coin would land ten or better
about 1.9% of the time. The rules move a reader, and this is the first time the
project can say that about text the reader had never met.

**Every complaint against the ruled arm is the same complaint.** Four of the
twelve notes fault it for missing structure, and no note faults it for anything
else structural or prosodic:

    c04  "scannability is reduced due to total lack of headings"   picked ruled anyway
    c05  "relying exclusively on prose when a table could've made
          things clearer"                                          picked ruled anyway
    d04  "A reads better in some parts because of the Impact
          bulleted list and its Action Items as a table"           picked ruled anyway
    d02  "more scannable because of the headings and bullets, and
          in the context of reading PRs, scannability is
          important"                                               LOST on this

Block counts for these twelve pairs, ruled against control: headings 26 vs 42,
lists 10 vs 18, tables 2 vs 5, code blocks 10 vs 20. The ruled arm carries about
half the structure. In the seven conversational prompts it carries no headings at
all, which is R04 doing exactly what R04 says.

This is the K1/K2/K4 gap the scorecard has been reporting as "the remaining gap,
not a success". A person has now put a price on it: scannability, and one lost
verdict out of twelve. **d02 says plainly that better prose can lose to worse
prose that is easier to scan**, and that is a finding about the rules rather than
about the reader.

**c01 is the other loss and it is the one to read again.** Neither arm had any
structure to argue about, 0 blocks against 1 code block, and no note was left.
It is the only pair where the ruled arm lost on prose alone.

## A defect no detector would have found

The word **"shape"** was flagged twice unprompted, in two different samples:

    c06  "The word 'shape' is overused ... 'Three things change shape once the
          delete is real' really sounds off to me"
    d02  "A minor thing in A is that it uses the overused 'shape'"

Measured, it is nearly invisible. Substrate A, per 1,000 words: v2 control 0.19
against 0.29 ruled; v1 control 0.26, R02 undivided 0.31, the split 0.42, without
R02 0.28. Four ruled arms all sit above their control and the counts are 4 to 8
hits, far too few to claim anything.

**The word is in the rules.** R09 reads "That shape performs insight rather than
delivering it." Whether an instruction seeds its own vocabulary into the output
is a question the harness has never asked, and it is cheap to ask: change the
word in R09 and re-run.

Two more one-off notes, both in the ruled arm, neither yet a pattern: "the one
that looks like less work and isn't", where the reader wanted "but isn't"; and
"you may be holding the quote", an idiom they did not know.

## What this does not settle

One reader. The plan is to put the same twelve pairs to other people, whose
answers stay in their own browsers until they send the table back. Repeats 2 and
3 of both v2 runs are unread and unspent.
