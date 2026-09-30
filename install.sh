#!/usr/bin/env bash
# Symlink every skill in this repo into ~/.claude/skills so the repo stays the source of truth.
# Idempotent. Run again after adding a skill. Use `--uninstall` to remove the links.
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEST="${CLAUDE_SKILLS_DIR:-$HOME/.claude/skills}"
mkdir -p "$DEST"
for dir in "$HERE"/skills/*/; do
  name="$(basename "$dir")"
  link="$DEST/$name"
  if [[ "${1:-}" == "--uninstall" ]]; then
    [[ -L "$link" ]] && rm "$link" && echo "removed $link"
    continue
  fi
  if [[ -e "$link" && ! -L "$link" ]]; then
    echo "skip: $link exists and is not a symlink" >&2
    continue
  fi
  ln -sfn "$dir" "$link"
  echo "$link -> $dir"
done
[[ "${1:-}" == "--uninstall" ]] || echo "Installed. Do not ALSO install this repo as a plugin: the skills would trigger twice (boss:boss and boss)."
