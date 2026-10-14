#!/usr/bin/env bash
# PreToolUse hook for Write|Edit: allow writes only under the directory given as $1
# (relative to the project root). Used to keep memory-enabled reviewers read-only.
set -euo pipefail
trap 'echo "Blocked: write-guard hook failed" >&2; exit 2' ERR  # fail closed

root="${CLAUDE_PROJECT_DIR:-$PWD}"
allowed="$(realpath -m "$root/$1")"
target="$(jq -r '.tool_input.file_path // empty')"

if [[ -z "$target" ]]; then
  echo "Blocked: no file_path in tool input" >&2
  exit 2
fi
[[ "$target" = /* ]] || target="$root/$target"
target="$(realpath -m "$target")"

if [[ "$target" == "$allowed" || "$target" == "$allowed"/* ]]; then
  exit 0
fi
echo "Blocked: this agent may only write under $1. Report the change to the owning agent instead." >&2
exit 2
