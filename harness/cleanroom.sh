#!/usr/bin/env bash
# Run one clean-room sample. Prompt on stdin, Claude's JSON result on stdout.
#
# Requires CLAUDE_CONFIG_DIR to point at a synthesized scratch config dir that
# already contains .credentials.json (run.py builds and tears this down).
#
# Usage: cleanroom.sh <a|b> <style-prompt-file|-> <model> <max-budget-usd>

set -euo pipefail

SUBSTRATE="$1"; STYLE="$2"; MODEL="$3"; BUDGET="$4"

: "${CLAUDE_CONFIG_DIR:?cleanroom.sh requires CLAUDE_CONFIG_DIR}"
[ -f "$CLAUDE_CONFIG_DIR/.credentials.json" ] || {
  echo "no credentials in scratch config dir" >&2; exit 64; }

# Tools are disallowed rather than absent: the schemas are still sent (measured
# 12,360 tokens), but nothing can fire. Pure-prose corpus needs none of them.
TOOLS=(Bash Read Write Edit MultiEdit Glob Grep Task WebFetch WebSearch
       NotebookEdit TodoWrite BashOutput KillShell Skill Agent Artifact
       SlashCommand ExitPlanMode)

ARGS=(
  -p
  --model "$MODEL"
  --output-format json
  --system-prompt-snapshot off
  --setting-sources ""
  --strict-mcp-config
  --disable-slash-commands
  --permission-mode dontAsk
  --permission-prompts none
  --disallowed-tools "${TOOLS[@]}"
  --max-budget-usd "$BUDGET"
)

# Substrate B replaces Claude Code's default system prompt with a minimal stub,
# so the style file is the only style instruction in play. Substrate A leaves
# the default prompt intact and measures what the style file adds on top of it.
if [ "$SUBSTRATE" = "b" ]; then
  ARGS+=(--system-prompt "You are a helpful assistant."
         --exclude-dynamic-system-prompt-sections)
fi

# Absent style file means the control arm: no style instruction at all.
if [ "$STYLE" != "-" ]; then
  ARGS+=(--append-system-prompt-file "$STYLE")
fi

# Echo the resolved argv to stderr so run.py can record it in the manifest.
printf 'ARGV %s\n' "$(printf '%q ' claude "${ARGS[@]}")" >&2

exec claude "${ARGS[@]}"
