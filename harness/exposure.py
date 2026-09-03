#!/usr/bin/env python3
"""A ledger of which samples the copyeditor has already been shown.

The blind read of 2026-09-03 was not blind. `make_verdict_reader.py` had already
put the opening paragraph of every substrate-A sample in front of the copyeditor
with its arm named -- "no rules at all" / "rules with the clauses" -- so by the
time they read a pair they had seen the top of both answers, labelled. The read
was lost and no galley knew it had spent the text.

A galley that names an arm burns the sample for every future blind comparison.
This records that spend so the next blind read can refuse to reuse it. Reading
without a label is recorded too, because familiarity is a weaker bias but still
a bias, and the ledger should show both.

The ledger is committed. It is evidence about the reader, not about the model,
and it cannot be reconstructed from the runs.
"""

from __future__ import annotations

import json
from pathlib import Path

LEDGER = Path(__file__).resolve().parent.parent / "verdicts" / "exposure.json"


def _load() -> list[dict]:
    if not LEDGER.is_file():
        return []
    return json.loads(LEDGER.read_text(encoding="utf-8"))


def record(script: str, run: str, keys: list[str], labelled: bool,
           what: str = "") -> None:
    """Note that a galley showed these samples. Idempotent per (script, run)."""
    rows = [r for r in _load() if not (r["script"] == script and r["run"] == run)]
    rows.append({"script": script, "run": run, "labelled": labelled,
                 "what": what, "keys": sorted(set(keys))})
    rows.sort(key=lambda r: (r["script"], r["run"]))
    LEDGER.parent.mkdir(exist_ok=True)
    LEDGER.write_text(json.dumps(rows, indent=2) + "\n", encoding="utf-8")


def burned(run: str, labelled_only: bool = True) -> set[str]:
    """Sample keys already shown from this run, and so unfit for a blind read."""
    out: set[str] = set()
    for r in _load():
        if r["run"] != run:
            continue
        if labelled_only and not r["labelled"]:
            continue
        out.update(r["keys"])
    return out


def report(run: str, keys: list[str]) -> str:
    """A line per galley that has spent any of these keys, or "" if none have."""
    want = set(keys)
    lines = []
    for r in sorted(_load(), key=lambda r: r["script"]):
        if r["run"] != run:
            continue
        hit = want & set(r["keys"])
        if hit:
            lines.append(f"    {r['script']}: {len(hit)} of {len(want)}"
                         f"{' WITH THE ARM NAMED' if r['labelled'] else ''}"
                         f"{' -- ' + r['what'] if r['what'] else ''}")
    return "\n".join(lines)
