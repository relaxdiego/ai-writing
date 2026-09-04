#!/usr/bin/env python3
"""Package the shipped rules as a standalone prose style guide.

The guide is the deliverable, not a file this repository keeps a copy of. It is
written to an absolute path outside the repo, normally the user's memory file,
so there is one copy on disk and nothing to drift.

The rule text comes verbatim from style/rules.md, because the wording is what
was measured; only the "Rnn - " prefix is stripped from each heading, since an
ID is an address in this project and means nothing to a reader elsewhere. The
two closing sections live here rather than in style/rules.md, because they are
guidance for a writer rather than instructions injected into a run.

The guide must read as though written from scratch. It names no rule ID, run,
metric, corpus, substrate or measurement, and it does not appeal to this
project's evidence. What the evidence bought is the wording, not a citation.
"""

import argparse
import re
import sys
from collections.abc import Iterable
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

PREAMBLE = """# Writing prose

These rules govern prose you write: replies, documents, commit bodies, comments,
anything a person reads. They take precedence over default habits of formatting
and phrasing. They do not govern code.
"""

CLOSING = """
## When two of these pull against each other

Structure and prose compete, and the reader's use of the page settles it. A
document that will be scanned, searched or returned to keeps its headings, its
lists and its tables, and the prose rules apply inside them. Writing that is a
pleasure to read start to finish is worth nothing to somebody who only needs the
one part they came for.

The cost runs the other way too. A set of parallel items is a list, and a grid is
a table. Reaching for a table because a table is allowed produces a grid with one
real dimension, and a checklist a reader works through with a finger on the page
is not improved by becoming a matrix.

## Words and habits to watch

None of these is a rule. Each is worth a second look in your own draft.

**"shape" as a noun.** "Three things change shape once the delete is real." The
verb is usually fine; the noun is the tic.

**A negation where a plain statement would do.** "These are known and current, not
edge cases you are unlikely to reach" makes the reader resolve two negations to
arrive at "you will hit these". A doubled negation is how a plain verdict stops
being plain.

**A qualifier that repeats the word it qualifies.** "The costs we are accepting,
and accepting knowingly." The repetition performs care instead of adding
anything.
"""

BANNED = re.compile(
    r"\bR\d\d\b|corpus|substrate|ablat|detector|taxonomy|eval\b|blind read|"
    r"copyeditor|control arm|noise band|per 1,?000 words|harness",
    re.I)


def build(rules_path: Path, only: Iterable[str] = (),
          ablate: Iterable[str] = ()) -> tuple[str, list[str]]:
    """The guide, and the rule ids it contains.

    This is the only place the shipped wording is assembled. harness/run.py
    --guide injects exactly this text and package_style writes exactly this
    text, so the document that is measured and the document that ships cannot
    differ. --only and --ablate select rules for an ablation arm; the wrapper
    around them is the same either way, because a wrapper that is cosmetic
    three times over turned out not to be cosmetic once (runs of 2026-09-04).
    """
    only, ablate = set(only), set(ablate)
    text = rules_path.read_text(encoding="utf-8")
    chunks = ("## " + text.split("\n## ", 1)[1]).split("\n## ")
    ids, out = [], []
    for chunk in chunks:
        chunk = chunk.lstrip("# ").rstrip()
        m = re.match(r"^(R\d+)\b", chunk)
        if not m:
            continue
        ids.append(m.group(1))
        if (only and m.group(1) not in only) or m.group(1) in ablate:
            continue
        title, body = chunk.split("\n", 1)
        title = re.sub(r"^R\d+\s+[—-]\s*", "", title)
        out.append((m.group(1), f"## {title}\n\n{body.strip()}"))
    if not ids:
        sys.exit(f"{rules_path}: no rules found")
    for r in (only | ablate) - set(ids):
        sys.exit(f"unknown rule id: {r}")
    if not out:
        sys.exit("no rules left after filtering")
    guide = PREAMBLE + "\n" + "\n\n".join(b for _, b in out) + "\n" + CLOSING
    return guide, [i for i, _ in out]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--rules", default=str(REPO / "style" / "rules.md"))
    ap.add_argument("--out", default=str(Path.home() / ".claude" / "CLAUDE.md"))
    args = ap.parse_args()

    guide, _ = build(Path(args.rules))

    leaks = sorted(set(m.group(0) for m in BANNED.finditer(guide)))
    if leaks:
        sys.exit("guide leaks project vocabulary: " + ", ".join(leaks))

    out = Path(args.out).resolve()
    if REPO in out.parents or out == REPO:
        sys.exit(f"refusing to write the guide inside the repo: {out}\n"
                 "The guide lives outside it so there is one copy and no drift.")

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(guide, encoding="utf-8")
    print(f"{out}  {len(guide.split())} words  no project vocabulary")
    return 0


if __name__ == "__main__":
    sys.exit(main())
