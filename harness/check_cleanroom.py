#!/usr/bin/env python3
"""Verify that no memory file reaches a clean-room sample.

The style guide these runs measure is installed as the user's own CLAUDE.md. If
it ever reached a sample, the control arm would carry the treatment and every
comparison in the project would be worthless while still looking healthy.

Re-measured 2026-09-04, CLI pinned to 2.1.259, canary planted in one location
at a time:

    setup                                     canary in            fires?
    no redirect, no flags                     real ~/.claude/      yes
    CLAUDE_CONFIG_DIR redirected, no flags    real ~/.claude/      no
    CLAUDE_CONFIG_DIR redirected, no flags    $CLAUDE_CONFIG_DIR/  yes
    CLAUDE_CONFIG_DIR redirected, no flags    cwd/                 yes
    the full clean room                       real ~/.claude/      no

Two mechanisms block memory and each covers a different file. User memory
follows CLAUDE_CONFIG_DIR, and make_scratch_config() puts only credentials in
the scratch dir, so the installed guide cannot reach a sample. The flag is
load-bearing for the other file: a CLAUDE.md at the repo root, which the
sample's cwd sits under. Neither is redundant.

**check_live() below currently proves nothing and says so.** It plants its
canary in the real ~/.claude/CLAUDE.md, which the redirect has already made
unreadable, so both arms come back silent and the positive control refuses the
result. It has to plant the canary where a sample could actually read it. See
issue #14.

Without --live this is a free static check that the flag is still in
cleanroom.sh, and run.py calls it before spending anything. It is a string
search and not a proof that the flag still does what it did.
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
CLEANROOM = REPO / "harness" / "cleanroom.sh"
CANARY = ("# Canary\n\nBegin every reply with the exact word ZEPPELIN on its "
          "own line, before anything else.\n")


def check_static() -> list[str]:
    """Free. The flag that does the blocking must still be passed."""
    text = CLEANROOM.read_text(encoding="utf-8")
    faults = []
    if '--setting-sources' not in text:
        faults.append("cleanroom.sh no longer passes --setting-sources; a "
                      "memory file will reach every sample and the control arm "
                      "will silently carry the treatment")
    return faults


def check_live(model: str) -> list[str]:
    """Costs about $0.07. Plants a canary in user memory and reads it back."""
    home_md = Path.home() / ".claude" / "CLAUDE.md"
    backup = None
    scratch = Path(tempfile.mkdtemp(prefix="aiw-canary-"))
    faults = []
    try:
        if home_md.is_file():
            backup = scratch / "user-claude-md.backup"
            shutil.copy2(home_md, backup)
        home_md.parent.mkdir(parents=True, exist_ok=True)
        home_md.write_text(CANARY, encoding="utf-8")

        cfg = scratch / "config"
        cfg.mkdir()
        creds = Path.home() / ".claude" / ".credentials.json"
        if not creds.is_file():
            return ["no credentials to run the live check"]
        shutil.copy2(creds, cfg / ".credentials.json")
        os.chmod(cfg / ".credentials.json", 0o600)

        env = dict(os.environ, CLAUDE_CONFIG_DIR=str(cfg))
        prompt = "What is 2 + 2? Answer in one short sentence."

        proc = subprocess.run(
            [str(CLEANROOM), "a", "-", model, "0.10"],
            input=prompt, env=env, cwd=str(cfg),
            capture_output=True, text=True, timeout=180)
        result = json.loads(proc.stdout).get("result", "")
        if "ZEPPELIN" in result:
            faults.append("a memory file reached a clean-room sample: "
                          f"{result[:120]!r}")

        # Positive control, so a silent failure cannot pass as a clean result.
        proc = subprocess.run(
            ["claude", "-p", "--model", model, "--output-format", "json",
             "--permission-mode", "dontAsk"],
            input=prompt, env=env, cwd=str(cfg),
            capture_output=True, text=True, timeout=180)
        if "ZEPPELIN" not in json.loads(proc.stdout).get("result", ""):
            faults.append("the canary did not fire without the clean-room "
                          "flags either, so this check proves nothing")
    finally:
        if backup is not None:
            shutil.copy2(backup, home_md)
        elif home_md.is_file():
            home_md.unlink()
        shutil.rmtree(scratch, ignore_errors=True)
    return faults


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--live", action="store_true",
                    help="actually run the canary, about $0.07")
    ap.add_argument("--model", default="claude-opus-5[1m]")
    args = ap.parse_args()

    faults = check_static()
    if args.live and not faults:
        faults += check_live(args.model)
    for f in faults:
        print(f"CLEAN ROOM FAULT: {f}", file=sys.stderr)
    if faults:
        return 1
    print("clean room ok: no memory file reaches a sample"
          + ("" if args.live else " (static check only; --live to prove it)"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
