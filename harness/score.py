#!/usr/bin/env python3
"""Score a run's samples against TAXONOMY.md and compare against a baseline.

Writes result.json (per-sample scores plus per-substrate aggregates) and, when
--against is given, report.md with deltas and whether each cleared the noise
band.

The band is 2x the pooled standard error of the difference between the two
arms' means. With 12 prompts there is no power for significance testing, so
this reports effect size against measured variance and says so.
"""

from __future__ import annotations

import argparse
import json
import math
import statistics as st
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from detectors import DETECTORS, score_text  # noqa: E402

REPO = Path(__file__).resolve().parent.parent
META = {mid: (name, unit, kind) for mid, name, unit, kind, _ in DETECTORS}


def score_run(run_dir: Path) -> dict:
    manifest = json.loads((run_dir / "manifest.json").read_text())
    per_sample = []
    for s in manifest["samples"]:
        if not s["ok"]:
            continue
        text = (run_dir / "samples" / f"{s['key']}.md").read_text(encoding="utf-8")
        per_sample.append({
            "key": s["key"], "substrate": s["substrate"], "prompt": s["prompt_id"],
            "register": s["register"], "scores": score_text(text),
        })

    agg = {}
    for sub in sorted({x["substrate"] for x in per_sample}):
        rows = [x["scores"] for x in per_sample if x["substrate"] == sub]
        agg[sub] = {}
        for mid, _, _, _, _ in DETECTORS:
            v = [r[mid] for r in rows]
            sd = st.stdev(v) if len(v) > 1 else 0.0
            agg[sub][mid] = {
                "mean": round(st.mean(v), 3), "sd": round(sd, 3),
                "sem": round(sd / math.sqrt(len(v)), 3) if v else 0.0,
                "n": len(v),
            }
    return {
        "run": run_dir.name,
        "arm": manifest["arm"],
        "style_sha256": manifest.get("style_sha256"),
        "model": manifest["model_requested"],
        "corpus": manifest["corpus_version"],
        "cost_usd": manifest["totals"]["cost_usd"],
        "failed": manifest["totals"]["failed"],
        "aggregates": agg,
        "samples": per_sample,
    }


def band(a: dict, b: dict) -> float:
    """Two pooled standard errors of the difference between the arms' means."""
    return 2 * math.sqrt(a["sem"] ** 2 + b["sem"] ** 2)


def report(cur: dict, base: dict, rules: list[str]) -> str:
    L = []
    L.append(f"# Eval report — {cur['run']}\n")
    L.append(f"- **arm** {cur['arm']}" + (f" · rules `{', '.join(rules)}`" if rules else ""))
    L.append(f"- **style sha256** `{(cur['style_sha256'] or '—')[:16]}`")
    L.append(f"- **model** `{cur['model']}` · **corpus** {cur['corpus']}")
    L.append(f"- **baseline** {base['run']} ({base['arm']})")
    L.append(f"- **cost** ${cur['cost_usd']:.2f} · **failed samples** {cur['failed']}\n")

    for sub in sorted(cur["aggregates"]):
        if sub not in base["aggregates"]:
            continue
        na = cur["aggregates"][sub]["S1"]["n"]
        nb = base["aggregates"][sub]["S1"]["n"]
        L.append(f"\n## Substrate {sub.upper()}  (n={nb} control → n={na} treatment)\n")
        L.append("| id | metric | unit | control | this run | delta | cleared band? |")
        L.append("|---|---|---|---:|---:|---:|---|")
        for kind in ("suppressed", "held-out", "context"):
            first = True
            for mid, name, unit, k, _ in DETECTORS:
                if k != kind:
                    continue
                if first:
                    L.append(f"| | **{kind}** | | | | | |")
                    first = False
                c, t = base["aggregates"][sub][mid], cur["aggregates"][sub][mid]
                d = t["mean"] - c["mean"]
                bd = band(c, t)
                mark = "**yes**" if abs(d) > bd else "no"
                arrow = "↓" if d < 0 else ("↑" if d > 0 else "·")
                L.append(f"| {mid} | {name} | {unit} | {c['mean']:.2f} | {t['mean']:.2f} "
                         f"| {arrow} {d:+.2f} | {mark} (±{bd:.2f}) |")
    L.append("\n\n*Band is two pooled standard errors of the difference between "
             "the arms' means. At 12 prompts there is no power for significance "
             "testing; this is effect size against measured variance.*\n")
    return "\n".join(L)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("run_dir")
    ap.add_argument("--against", help="baseline run dir to compare against")
    ap.add_argument("--rules", default="", help="rule ids active, for the report header")
    args = ap.parse_args()

    run = Path(args.run_dir)
    res = score_run(run)
    (run / "result.json").write_text(json.dumps(res, indent=2), encoding="utf-8")
    print(f"scored {len(res['samples'])} samples → {run / 'result.json'}")

    if args.against:
        base_dir = Path(args.against)
        bp = base_dir / "result.json"
        base = json.loads(bp.read_text()) if bp.is_file() else score_run(base_dir)
        if not bp.is_file():
            bp.write_text(json.dumps(base, indent=2), encoding="utf-8")
        rules = [r.strip() for r in args.rules.split(",") if r.strip()]
        md = report(res, base, rules)
        (run / "report.md").write_text(md, encoding="utf-8")
        print(md)
    return 0


if __name__ == "__main__":
    sys.exit(main())
