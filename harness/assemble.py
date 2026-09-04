#!/usr/bin/env python3
"""Assemble the prompt actually injected, which is the guide that ships.

The wording is what the evidence buys, so the document measured has to be the
document installed. Both are built by package_style.build; this script only
writes it to a file and prints the sha that goes into the manifest.

Rules are addressed by ID so a metric change can be attributed to a specific
instruction. --only runs a named subset; --ablate drops one rule and keeps the
rest. The IDs live in style/rules.md and never reach the injected text.
"""

import argparse
import hashlib
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
import package_style  # noqa: E402  (harness-local, after REPO is defined)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--rules", default=str(REPO / "style" / "rules.md"))
    ap.add_argument("--out", default=str(REPO / "build" / "style.prompt.md"))
    ap.add_argument("--only", default="", help="comma-separated rule ids to include")
    ap.add_argument("--ablate", default="", help="comma-separated rule ids to drop")
    args = ap.parse_args()

    only = {x.strip() for x in args.only.split(",") if x.strip()}
    drop = {x.strip() for x in args.ablate.split(",") if x.strip()}
    text, kept = package_style.build(Path(args.rules), only=only, ablate=drop)

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text, encoding="utf-8")
    sha = hashlib.sha256(out.read_bytes()).hexdigest()
    print(f"{out}  rules={','.join(kept)}  sha256={sha[:16]}  "
          f"{len(text.split())} words")
    return 0


if __name__ == "__main__":
    sys.exit(main())
