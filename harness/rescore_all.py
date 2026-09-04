#!/usr/bin/env python3
"""Re-score every run and rebuild every report, after a detector changes.

Raw outputs are kept forever precisely so a detector written or corrected later
can be backfilled across all history (DESIGN.md 10). Three detector faults have
been found and fixed so far, each by reading samples rather than aggregates, so
the backfill is a script rather than another one-off.

Every report names the baseline it was built against in its own header, so each
file is rebuilt against the arm it was originally compared with and no report
silently changes meaning. Reports whose header cannot be parsed are listed and
left alone.

    python3 harness/rescore_all.py            # rebuild, print what moved
    python3 harness/rescore_all.py --metric S6
"""

import argparse
import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
import score  # noqa: E402  (harness-local)

BASELINE_LINE = re.compile(r"^- \*\*baseline\*\* (\S+)", re.M)
RULES_LINE = re.compile(r"rules `([^`]*)`")


def run_dirs() -> list[Path]:
    out = [d for d in sorted(REPO.glob("baseline/*")) if (d / "samples").is_dir()]
    out += [d for d in sorted(REPO.glob("runs/*")) if (d / "samples").is_dir()]
    return out


def find_dir(name: str) -> Path | None:
    for parent in ("runs", "baseline"):
        p = REPO / parent / name
        if (p / "samples").is_dir():
            return p
    return None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--metric", default="S6", help="metric to report movement on")
    args = ap.parse_args()

    dirs = run_dirs()
    before = {}
    for d in dirs:
        rp = d / "result.json"
        if rp.is_file():
            old = json.loads(rp.read_text())
            for sub, mets in old.get("aggregates", {}).items():
                if args.metric in mets:
                    before[(d.name, sub)] = mets[args.metric]["mean"]

    scored = {}
    for d in dirs:
        res = score.score_run(d)
        (d / "result.json").write_text(json.dumps(res, indent=2), encoding="utf-8")
        scored[d.name] = res
        print(f"scored {d.name}")

    unparsed = []
    for d in dirs:
        for rep in sorted(d.glob("report*.md")):
            head = rep.read_text(encoding="utf-8")[:600]
            m = BASELINE_LINE.search(head)
            base_dir = find_dir(m.group(1)) if m else None
            if base_dir is None:
                unparsed.append(str(rep.relative_to(REPO)))
                continue
            rm = RULES_LINE.search(head)
            rules = [r.strip() for r in (rm.group(1) if rm else "").split(",") if r.strip()]
            jp = d / "judge.json"
            judge = json.loads(jp.read_text()) if jp.is_file() else None
            md = score.report(scored[d.name], scored[base_dir.name], rules, judge)
            rep.write_text(md, encoding="utf-8")
            print(f"rebuilt {rep.relative_to(REPO)}  vs {base_dir.name}")

    print(f"\n{args.metric} mean, before -> after")
    for d in dirs:
        for sub, mets in scored[d.name].get("aggregates", {}).items():
            if args.metric not in mets:
                continue
            after = mets[args.metric]["mean"]
            old = before.get((d.name, sub))
            if old is None or abs(after - old) < 1e-9:
                continue
            print(f"  {d.name:44} {sub}  {old:8.2f} -> {after:8.2f}")

    if unparsed:
        print("\nreports left alone, header not parsed:")
        for u in unparsed:
            print(" ", u)
    return 0


if __name__ == "__main__":
    sys.exit(main())
