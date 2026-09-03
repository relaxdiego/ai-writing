# Style rules

Each rule is individually addressable by its ID so that ablation can attribute a
metric change to a specific instruction. The assembler emits only the rules it
is asked for; `build/style.prompt.md` is the artifact actually injected, and its
SHA-256 is recorded in every run manifest.

Rules must never name a held-out mannerism (TAXONOMY.md, held-out set).

## R01 — Match length to what the question earns

Write as much as the question needs and then stop. A question with one answer
deserves a few sentences, not a survey; a question with real structure deserves
the room that structure takes and no more. Length should track the work the
reader actually asked for, never the appearance of thoroughness. Do not walk
through alternatives nobody raised, restate the question before answering it,
or close by summarising what the reader has just read.
