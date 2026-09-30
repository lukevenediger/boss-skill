#!/usr/bin/env bash
# Build a scratch repo with one planted bug for an end-to-end boss mini-run.
# Usage: bash tests/toy-repo.sh [<dir>]   (default: /tmp/boss-toy)
# The bug: `lib/split.sh` drops the last field when the input has no trailing comma.
# `bash gate.sh` runs the tests; `tests/split.test.sh` currently passes only because the
# failing case is commented out — a real fix adds the case, watches it fail, then fixes split.sh.
set -euo pipefail
DIR="${1:-/tmp/boss-toy}"
rm -rf "$DIR"; mkdir -p "$DIR/lib" "$DIR/tests"; cd "$DIR"
git init -q -b main
cat > README.md <<'EOF'
# toy

A tiny CSV field splitter with one planted bug, for exercising a boss run end to end.

- `bash gate.sh` — runs every test under tests/
- `bash lib/split.sh "a,b,c"` — prints one field per line
EOF
cat > lib/split.sh <<'EOF'
#!/usr/bin/env bash
# Print one field per line. BUG: the loop stops before the last field when the input
# does not end with a comma.
s="$1,"
while [[ "$s" == *,* ]]; do
  f="${s%%,*}"; s="${s#*,}"
  if [[ -n "$s" ]]; then printf '%s\n' "$f"; fi
done
EOF
cat > tests/split.test.sh <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
here="$(cd "$(dirname "$0")/.." && pwd)"
out="$(bash "$here/lib/split.sh" "a,b,")"
[[ "$out" == $'a\nb' ]] && echo "PASS trailing comma" || { echo "FAIL trailing comma: $out"; exit 1; }
# T1.1: no trailing comma — currently disabled; a fix must enable it and make it pass
# out="$(bash "$here/lib/split.sh" "a,b,c")"
# [[ "$out" == $'a\nb\nc' ]] && echo "PASS no trailing comma" || { echo "FAIL no trailing comma: $out"; exit 1; }
EOF
cat > gate.sh <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
rc=0
for t in tests/*.test.sh; do bash "$t" || rc=1; done
[[ $rc -eq 0 ]] && echo "gate: green" || { echo "gate: red"; exit 1; }
EOF
git add -A && git commit -qm "toy: csv splitter with a planted last-field bug"
git checkout -qb run/fix
echo "toy repo at $DIR (branch run/fix). Planted bug: bash lib/split.sh 'a,b,c' drops 'c'."
