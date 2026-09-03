#!/usr/bin/env python3
"""Assemble style/rules.md into the prompt actually injected.

Rules are addressed by ID so a metric change can be attributed to a specific
instruction. --only runs a named subset; --ablate drops one rule and keeps the
rest. The emitted file's SHA-256 goes into every run manifest.
"""

import argparse
import hashlib
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent


def parse(path: Path) -> list[tuple[str, str]]:
    text = path.read_text(encoding="utf-8")
    body = text.split("\n## ", 1)
    if len(body) < 2:
        sys.exit(f"{path}: no rules found")
    out = []
    for chunk in ("## " + body[1]).split("\n## "):
        chunk = chunk.lstrip("# ").strip()
        m = re.match(r"^(R\d+)\b", chunk)
        if m:
            out.append((m.group(1), "## " + chunk))
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--rules", default=str(REPO / "style" / "rules.md"))
    ap.add_argument("--out", default=str(REPO / "build" / "style.prompt.md"))
    ap.add_argument("--only", default="", help="comma-separated rule ids to include")
    ap.add_argument("--ablate", default="", help="comma-separated rule ids to drop")
    args = ap.parse_args()

    rules = parse(Path(args.rules))
    ids = [r[0] for r in rules]
    only = {x.strip() for x in args.only.split(",") if x.strip()}
    drop = {x.strip() for x in args.ablate.split(",") if x.strip()}
    for r in (only | drop) - set(ids):
        sys.exit(f"unknown rule id: {r}")

    kept = [(i, b) for i, b in rules if (not only or i in only) and i not in drop]
    if not kept:
        sys.exit("no rules left after filtering")

    header = ("The following rules govern how you write prose. They take "
              "precedence over any default habits of formatting or phrasing.\n")
    text = header + "\n" + "\n\n".join(b for _, b in kept) + "\n"

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text, encoding="utf-8")
    sha = hashlib.sha256(out.read_bytes()).hexdigest()
    print(f"{out}  rules={','.join(i for i, _ in kept)}  sha256={sha[:16]}  "
          f"{len(text.split())} words")
    return 0


if __name__ == "__main__":
    sys.exit(main())
