#!/usr/bin/env python3
"""Clean-room sample runner.

Executes the frozen corpus against Claude Code under a synthesized config
directory, one sample per (substrate, arm, prompt, repeat), and writes raw
outputs plus a provenance manifest.

The corpus is never mutated. Failed samples are recorded, not dropped: a failure
mode correlated with the treatment would bias results invisibly.
"""

from __future__ import annotations

import argparse
import atexit
import concurrent.futures as futures
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
CLEANROOM = REPO / "harness" / "cleanroom.sh"
REAL_CREDS = Path.home() / ".claude" / ".credentials.json"

DEFAULT_MODEL = "claude-opus-5[1m]"
DEFAULT_BUDGET = "1.00"
MAX_ATTEMPTS = 3
OK_STOP_REASONS = {"end_turn", "stop_sequence"}


# ---------------------------------------------------------------- corpus ----

@dataclass(frozen=True)
class Prompt:
    id: str
    register: str
    name: str
    body: str
    path: str


def load_corpus(version: str) -> list[Prompt]:
    root = REPO / "corpus" / version
    if not root.is_dir():
        sys.exit(f"no corpus at {root}")
    prompts: list[Prompt] = []
    for path in sorted(root.rglob("*.md")):
        text = path.read_text(encoding="utf-8")
        m = re.match(r"^---\n(.*?)\n---\n(.*)$", text, re.DOTALL)
        if not m:
            sys.exit(f"{path}: missing frontmatter")
        meta = {}
        for line in m.group(1).splitlines():
            if ":" in line:
                k, v = line.split(":", 1)
                meta[k.strip()] = v.strip()
        prompts.append(Prompt(
            id=meta["id"], register=meta["register"], name=meta["name"],
            body=m.group(2).strip(),
            path=str(path.relative_to(REPO)),
        ))
    ids = [p.id for p in prompts]
    if len(set(ids)) != len(ids):
        sys.exit(f"duplicate prompt ids in {root}")
    return prompts


# ------------------------------------------------------------ clean room ----

def make_scratch_config() -> Path:
    """Synthesize an isolated CLAUDE_CONFIG_DIR.

    Both stronger isolation levers break subscription auth: --bare and a bare
    redirected config dir each fail with "Not logged in". Copying credentials
    into the scratch dir is the only route that keeps OAuth working, so the
    token is copied at mode 600 and removed on exit.
    """
    if not REAL_CREDS.is_file():
        sys.exit(f"no credentials at {REAL_CREDS}; run `claude` and /login first")
    scratch = Path(tempfile.mkdtemp(prefix="aiw-cleanroom-", dir=REPO / ".scratch"))
    dest = scratch / ".credentials.json"
    shutil.copyfile(REAL_CREDS, dest)
    os.chmod(dest, 0o600)
    os.chmod(scratch, 0o700)
    atexit.register(lambda: shutil.rmtree(scratch, ignore_errors=True))
    return scratch


def config_dir_inventory(scratch: Path) -> list[str]:
    """Record what the clean room actually contained, for the manifest."""
    return sorted(
        str(p.relative_to(scratch)) + ("/" if p.is_dir() else "")
        for p in scratch.rglob("*")
    )


# ---------------------------------------------------------------- sample ----

@dataclass
class Sample:
    key: str
    substrate: str
    arm: str
    prompt_id: str
    register: str
    repeat: int
    ok: bool = False
    failure: str | None = None
    attempts: int = 0
    text: str = ""
    cost_usd: float = 0.0
    duration_ms: int = 0
    stop_reason: str | None = None
    num_turns: int | None = None
    session_id: str | None = None
    model_usage: dict = field(default_factory=dict)


def run_sample(sample: Sample, prompt: Prompt, scratch: Path, style: str,
               model: str, budget: str, argv_sink: dict) -> Sample:
    env = dict(os.environ)
    env["CLAUDE_CONFIG_DIR"] = str(scratch)
    env["CLAUDE_CODE_DISABLE_AUTO_MEMORY"] = "1"
    cmd = [str(CLEANROOM), sample.substrate, style, model, budget]

    delay = 4.0
    for attempt in range(1, MAX_ATTEMPTS + 1):
        sample.attempts = attempt
        try:
            proc = subprocess.run(
                cmd, input=prompt.body, env=env, cwd=str(scratch),
                capture_output=True, text=True, timeout=600,
            )
        except subprocess.TimeoutExpired:
            sample.failure = "timeout"
            time.sleep(delay); delay *= 2
            continue

        for line in proc.stderr.splitlines():
            if line.startswith("ARGV "):
                argv_sink.setdefault(f"{sample.substrate}/{sample.arm}", line[5:].strip())

        if proc.returncode != 0 and not proc.stdout.strip():
            sample.failure = f"exit {proc.returncode}: {proc.stderr.strip()[:300]}"
            time.sleep(delay); delay *= 2
            continue

        try:
            data = json.loads(proc.stdout)
        except json.JSONDecodeError:
            sample.failure = f"unparseable output: {proc.stdout.strip()[:300]}"
            time.sleep(delay); delay *= 2
            continue

        sample.cost_usd = data.get("total_cost_usd") or 0.0
        sample.duration_ms = data.get("duration_ms") or 0
        sample.stop_reason = data.get("stop_reason")
        sample.num_turns = data.get("num_turns")
        sample.session_id = data.get("session_id")
        sample.model_usage = data.get("modelUsage") or {}
        text = (data.get("result") or "").strip()

        if data.get("is_error"):
            sample.failure = f"api error: {text[:300]}"
            time.sleep(delay); delay *= 2
            continue
        if sample.stop_reason not in OK_STOP_REASONS:
            sample.failure = f"stop_reason={sample.stop_reason}"
            sample.text = text
            return sample          # truncation is a finding, not a transient
        if not text:
            sample.failure = "empty output"
            time.sleep(delay); delay *= 2
            continue

        sample.text = text
        sample.ok = True
        sample.failure = None
        return sample

    return sample


# ------------------------------------------------------------------ main ----

def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git_sha() -> str:
    try:
        out = subprocess.run(["git", "rev-parse", "HEAD"], cwd=REPO,
                             capture_output=True, text=True)
        return out.stdout.strip() or "uncommitted"
    except Exception:
        return "unknown"


def cli_version() -> str:
    out = subprocess.run(["claude", "--version"], capture_output=True, text=True)
    return out.stdout.strip()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", required=True, help="output directory for this run")
    ap.add_argument("--corpus", default="v1")
    ap.add_argument("--arm", choices=["control", "treatment"], default="control")
    ap.add_argument("--style", default=None,
                    help="assembled style prompt file (treatment arm only)")
    ap.add_argument("--substrates", default="a,b")
    ap.add_argument("--runs-a", type=int, default=3)
    ap.add_argument("--runs-b", type=int, default=5)
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--budget", default=DEFAULT_BUDGET, help="max USD per sample")
    ap.add_argument("--concurrency", type=int, default=4)
    ap.add_argument("--only", default="", help="comma-separated prompt ids (smoke tests)")
    ap.add_argument("--label", default="", help="note recorded in the manifest")
    args = ap.parse_args()

    if args.arm == "treatment" and not args.style:
        sys.exit("--arm treatment requires --style")
    style = args.style or "-"
    if style != "-" and not Path(style).is_file():
        sys.exit(f"style file not found: {style}")

    prompts = load_corpus(args.corpus)
    if args.only:
        keep = {x.strip() for x in args.only.split(",")}
        prompts = [p for p in prompts if p.id in keep]
        if not prompts:
            sys.exit(f"--only matched no prompts")
    substrates = [s.strip() for s in args.substrates.split(",") if s.strip()]
    runs = {"a": args.runs_a, "b": args.runs_b}

    out = Path(args.out)
    (out / "samples").mkdir(parents=True, exist_ok=True)
    (REPO / ".scratch").mkdir(exist_ok=True)
    scratch = make_scratch_config()

    queue: list[tuple[Sample, Prompt]] = []
    for sub in substrates:
        for p in prompts:
            for r in range(1, runs[sub] + 1):
                key = f"{sub}-{args.arm}-{p.id}-r{r}"
                queue.append((Sample(key, sub, args.arm, p.id, p.register, r), p))

    started = datetime.now(timezone.utc)
    print(f"corpus {args.corpus}: {len(prompts)} prompts | arm={args.arm} | "
          f"substrates={','.join(substrates)} | {len(queue)} samples", flush=True)

    argv_sink: dict[str, str] = {}
    done: list[Sample] = []

    def execute(item):
        s, p = item
        return run_sample(s, p, scratch, style, args.model, args.budget, argv_sink)

    # One serial sample per substrate warms that prefix's prompt cache. Measured:
    # a cache-warm repeat cost $0.0075 against $0.1249 cold, so paying 2 cold
    # samples up front beats letting 4 parallel workers all miss at once.
    warm = {}
    for sub in substrates:
        for i, (s, p) in enumerate(queue):
            if s.substrate == sub:
                warm[i] = True
                break
    for i in sorted(warm):
        s = execute(queue[i])
        done.append(s)
        print(f"  warm {s.key}: {'ok' if s.ok else 'FAIL ' + str(s.failure)} "
              f"${s.cost_usd:.4f}", flush=True)

    rest = [item for i, item in enumerate(queue) if i not in warm]
    with futures.ThreadPoolExecutor(max_workers=args.concurrency) as pool:
        for n, s in enumerate(pool.map(execute, rest), 1):
            done.append(s)
            print(f"  [{n}/{len(rest)}] {s.key}: "
                  f"{'ok' if s.ok else 'FAIL ' + str(s.failure)} "
                  f"${s.cost_usd:.4f} {len(s.text.split())}w", flush=True)

    for s in done:
        if s.text:
            (out / "samples" / f"{s.key}.md").write_text(s.text, encoding="utf-8")

    failures = [s for s in done if not s.ok]
    total_cost = sum(s.cost_usd for s in done)
    finished = datetime.now(timezone.utc)

    manifest = {
        "schema": 1,
        "label": args.label,
        "started_utc": started.isoformat(),
        "finished_utc": finished.isoformat(),
        "arm": args.arm,
        "substrates": substrates,
        "runs_per_prompt": {s: runs[s] for s in substrates},
        "corpus_version": args.corpus,
        "corpus_prompts": [{"id": p.id, "register": p.register,
                            "path": p.path,
                            "sha256": sha256_file(REPO / p.path)} for p in prompts],
        "style_file": style,
        "style_sha256": sha256_file(Path(style)) if style != "-" else None,
        "model_requested": args.model,
        "cli_version": cli_version(),
        "git_sha": git_sha(),
        "argv": argv_sink,
        "config_dir_inventory": config_dir_inventory(scratch),
        "concurrency": args.concurrency,
        "budget_per_sample_usd": args.budget,
        "totals": {
            "samples": len(done),
            "ok": len(done) - len(failures),
            "failed": len(failures),
            "cost_usd": round(total_cost, 6),
        },
        "samples": [asdict(s) for s in sorted(done, key=lambda x: x.key)],
    }
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    print(f"\n{len(done) - len(failures)}/{len(done)} ok | "
          f"${total_cost:.4f} | {(finished - started).total_seconds():.0f}s | {out}")
    if failures:
        print(f"\n{len(failures)} FAILED (recorded, excluded from metrics):")
        for s in failures:
            print(f"  {s.key}: {s.failure}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
