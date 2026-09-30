#!/usr/bin/env bash
# Test suite for the boss-protocol scripts. Plain bash; no framework.
# Run: bash tests/scripts.test.sh
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SCRIPTS="$REPO/skills/boss-protocol/scripts"
GOLDEN="$REPO/tests/golden"
export BOSS_NOW="2026-09-30T10:00:00"

pass_count=0
fail_count=0
failures=()

fail() { echo "  assert failed: $*" >&2; exit 1; }
assert_eq() { [ "$1" == "$2" ] || fail "expected [$2] got [$1]${3:+ ($3)}"; }
assert_file() { [ -f "$1" ] || fail "missing file $1"; }
assert_dir() { [ -d "$1" ] || fail "missing dir $1"; }
assert_contains() { grep -qF -- "$2" "$1" || fail "$1 does not contain [$2]"; }

fresh_home() {
  BOSS_HOME="$(mktemp -d "${TMPDIR:-/tmp}/boss-test.XXXXXX")"
  export BOSS_HOME
}

init_run() {
  bash "$SCRIPTS/boss-run" init w1 --title "W1 ingest" --repo /tmp/repo --branch feat/w1 --tz Africa/Johannesburg >/dev/null
}

say() { bash "$SCRIPTS/boss-say" "$@"; }
state() { bash "$SCRIPTS/boss-state" "$@"; }
apply_lines() { printf '%s\n' "$@" | state apply; }
state_json() { cat "$BOSS_HOME/runs/w1/state.json"; }

# ---------------------------------------------------------------- cases

case_run_init_creates_tree() {
  fresh_home; init_run
  assert_dir "$BOSS_HOME/runs/w1/evidence"
  assert_dir "$BOSS_HOME/runs/w1/pages"
  assert_file "$BOSS_HOME/runs/w1/run.json"
  assert_file "$BOSS_HOME/runs/w1/conversation.jsonl"
  assert_eq "$(wc -c < "$BOSS_HOME/runs/w1/conversation.jsonl" | tr -d ' ')" "0" "conversation empty"
  assert_eq "$(cat "$BOSS_HOME/current")" "w1" "current pointer"
  local rj="$BOSS_HOME/runs/w1/run.json"
  assert_eq "$(jq -r .id "$rj")" "w1"
  assert_eq "$(jq -r .title "$rj")" "W1 ingest"
  assert_eq "$(jq -r .repo "$rj")" "/tmp/repo"
  assert_eq "$(jq -r .branch "$rj")" "feat/w1"
  assert_eq "$(jq -r .tz "$rj")" "Africa/Johannesburg"
  assert_eq "$(jq -r .started "$rj")" "2026-09-30"
  assert_eq "$(jq -r .tools_dir "$rj")" "$SCRIPTS" "tools_dir"
  assert_eq "$(jq -c '[.roles[] | .role]' "$rj")" '["boss","dev","tester","status"]'
  assert_eq "$(jq -c '[.roles[] | .session]' "$rj")" '["w1-boss","w1-dev","w1-tester","w1-status"]'
  assert_eq "$(jq -c '[.roles[] | .model]' "$rj")" '["fable","opus","sonnet","opus"]'
  assert_eq "$(jq -c .pages "$rj")" '{}'
  # show prints run.json
  assert_eq "$(bash "$SCRIPTS/boss-run" show | jq -r .id)" "w1"
}

case_run_init_refuses_overwrite() {
  fresh_home; init_run
  echo '{"id":"w1"}' > "$BOSS_HOME/runs/w1/conversation.jsonl"
  local rc=0
  bash "$SCRIPTS/boss-run" init w1 --tz UTC >/dev/null 2>&1 || rc=$?
  [ "$rc" -ne 0 ] || fail "second init should fail"
  assert_eq "$(cat "$BOSS_HOME/runs/w1/conversation.jsonl")" '{"id":"w1"}' "conversation untouched"
  bash "$SCRIPTS/boss-run" init w1 --tz UTC --force >/dev/null
  assert_eq "$(jq -r .tz "$BOSS_HOME/runs/w1/run.json")" "UTC" "force overwrote"
}

case_run_init_custom_roles() {
  fresh_home
  bash "$SCRIPTS/boss-run" init w2 --tz UTC --role boss=w2-boss=fable --role reviewer=w2-rev=opus >/dev/null
  assert_eq "$(jq -c '[.roles[] | [.role,.session,.model]]' "$BOSS_HOME/runs/w2/run.json")" '[["boss","w2-boss","fable"],["reviewer","w2-rev","opus"]]'
  assert_eq "$(cat "$BOSS_HOME/current")" "w2"
}

case_run_set_page() {
  fresh_home; init_run
  bash "$SCRIPTS/boss-run" set-page status https://example.test/s >/dev/null
  bash "$SCRIPTS/boss-run" set-page conversation https://example.test/c >/dev/null
  assert_eq "$(jq -c .pages "$BOSS_HOME/runs/w1/run.json")" '{"status":"https://example.test/s","conversation":"https://example.test/c"}'
}

case_run_close_marks_closed() {
  fresh_home; init_run
  local out
  out="$(bash "$SCRIPTS/boss-run" close)"
  assert_eq "$(jq -r .closed "$BOSS_HOME/runs/w1/run.json")" "2026-09-30T10:00:00+02:00" "closed ts"
  echo "$out" | grep -qi "deferred defects" || fail "checklist mentions deferred defects"
  echo "$out" | grep -qi "OUTCOME" || fail "checklist mentions OUTCOME"
  echo "$out" | grep -qi "memory" || fail "checklist mentions memory"
  echo "$out" | grep -qi "sessions" || fail "checklist mentions sessions"
  echo "$out" | grep -qF "$BOSS_HOME/runs/w1" || fail "prints run dir"
}

case_say_assigns_sequential_ids() {
  fresh_home; init_run
  say --from boss --to dev --re RUN --subject "first" </dev/null >/dev/null
  say --from dev --to boss --re M1 --reply M1 --subject "second" </dev/null >/dev/null
  local f="$BOSS_HOME/runs/w1/conversation.jsonl"
  assert_eq "$(wc -l < "$f" | tr -d ' ')" "2"
  assert_eq "$(jq -r .id "$f" | paste -sd, -)" "M1,M2"
  assert_eq "$(sed -n 2p "$f" | jq -r '[.from,.to,.re,.reply_to,.subject,.body] | @csv')" '"dev","boss","M1","M1","second",""'
  assert_eq "$(sed -n 1p "$f" | jq -r .reply_to)" "null"
  assert_eq "$(sed -n 1p "$f" | jq -r .ts)" "2026-09-30T10:00:00+02:00"
  assert_eq "$(sed -n 1p "$f" | jq -c 'keys')" '["body","from","id","re","reply_to","subject","to","ts"]'
}

case_say_stdout_golden() {
  fresh_home; init_run
  local body expected actual
  body=$'Fix pushed.\n\n```evidence\ncmd: pnpm gate\nexit: 0\n```'
  expected=$'[M1 dev→boss re:D3 reply:M2] Fix pushed for D3: 98aadda, drift-guard test added\n\nFix pushed.\n\n```evidence\ncmd: pnpm gate\nexit: 0\n```'
  actual="$(printf '%s\n' "$body" | say --from dev --to boss --re D3 --reply M2 --subject "Fix pushed for D3: 98aadda, drift-guard test added")"
  assert_eq "$actual" "$expected" "stdout golden with body"
  # body from file, no reply
  printf 'from file\n' > "$BOSS_HOME/body.txt"
  actual="$(say --from tester --to boss --re T1.2 --subject "T1.2 PASS" --body-file "$BOSS_HOME/body.txt" </dev/null)"
  assert_eq "$actual" $'[M2 tester→boss re:T1.2] T1.2 PASS\n\nfrom file'
  # no body: header only
  actual="$(say --from owner --to boss --re OWNER --subject "Approved" </dev/null)"
  assert_eq "$actual" "[M3 owner→boss re:OWNER] Approved"
  # inline --body
  actual="$(say --from dev --to boss --re D1 --subject "Fix committed, push blocked for D1: abc1234 — no remote" --body "root cause: x" </dev/null)"
  assert_eq "$actual" $'[M4 dev→boss re:D1] Fix committed, push blocked for D1: abc1234 — no remote\n\nroot cause: x' "inline --body"
  # --body and --body-file together is a validation error, nothing appended
  set +e; say --from dev --to boss --re D1 --subject "x" --body "a" --body-file "$BOSS_HOME/body.txt" </dev/null >/dev/null 2>&1; rc=$?; set -e
  assert_eq "$rc" "2" "--body with --body-file exits 2"
  assert_eq "$(wc -l < "$BOSS_HOME/runs/w1/conversation.jsonl" | tr -d ' ')" "4" "nothing appended on the rejected send"
  assert_eq "$(sed -n 1p "$BOSS_HOME/runs/w1/conversation.jsonl" | jq -r .body)" "$body" "body stored verbatim"
}

case_say_rejects_invalid() {
  fresh_home; init_run
  local rc
  rc=0; say --from nobody --to boss --re RUN --subject "x" </dev/null >/dev/null 2>&1 || rc=$?
  assert_eq "$rc" "2" "bad from role"
  rc=0; say --from boss --to ghost --re RUN --subject "x" </dev/null >/dev/null 2>&1 || rc=$?
  assert_eq "$rc" "2" "bad to role"
  rc=0; say --from boss --to dev --re T1 --subject "x" </dev/null >/dev/null 2>&1 || rc=$?
  assert_eq "$rc" "2" "bad re"
  rc=0; say --from boss --to dev --re RUN --subject $'two\nlines' </dev/null >/dev/null 2>&1 || rc=$?
  assert_eq "$rc" "2" "multi-line subject"
  rc=0; say --from boss --to dev --re RUN --subject "$(printf 'x%.0s' {1..201})" </dev/null >/dev/null 2>&1 || rc=$?
  assert_eq "$rc" "2" "subject too long"
  rc=0; say --from boss --to dev --re RUN --reply 7 --subject "x" </dev/null >/dev/null 2>&1 || rc=$?
  assert_eq "$rc" "2" "bad reply"
  local err
  err="$(say --from nobody --to boss --re RUN --subject "x" </dev/null 2>&1 >/dev/null || true)"
  assert_eq "$(printf '%s' "$err" | wc -l | tr -d ' ')" "0" "one-line reason"
  [ -n "$err" ] || fail "reason printed"
  assert_eq "$(wc -c < "$BOSS_HOME/runs/w1/conversation.jsonl" | tr -d ' ')" "0" "nothing appended"
}

case_say_parallel_unique_ids() {
  fresh_home; init_run
  local i
  for i in $(seq 1 20); do
    say --from boss --to dev --re RUN --subject "parallel $i" </dev/null >/dev/null &
  done
  wait
  local f="$BOSS_HOME/runs/w1/conversation.jsonl"
  assert_eq "$(wc -l < "$f" | tr -d ' ')" "20" "20 lines"
  while IFS= read -r line; do printf '%s' "$line" | jq -e . >/dev/null || fail "invalid json: $line"; done < "$f"
  assert_eq "$(jq -r .id "$f" | sed 's/^M//' | sort -n | paste -sd, -)" "$(seq 1 20 | paste -sd, -)" "ids M1..M20"
  assert_eq "$(jq -r .id "$f" | sort -u | wc -l | tr -d ' ')" "20" "unique"
}

case_state_init() {
  fresh_home; init_run
  state init >/dev/null
  local s="$BOSS_HOME/runs/w1/state.json"
  assert_file "$s"
  assert_eq "$(jq -r .version "$s")" "0"
  assert_eq "$(jq -c .run "$s")" '{"id":"w1","title":"W1 ingest","started":"2026-09-30","tz":"Africa/Johannesburg"}'
  assert_eq "$(jq -c '[.phases,.defects,.owner_calls,.log,.ambiguous]' "$s")" '[[],[],[],[],[]]'
  assert_eq "$(jq -r .mood "$s")" "idle"
  assert_eq "$(jq -r .mood_override "$s")" "null"
  assert_eq "$(jq -c '[.team[] | [.role,.session,.model,.state]]' "$s")" '[["boss","w1-boss","fable","dormant"],["dev","w1-dev","opus","dormant"],["tester","w1-tester","sonnet","dormant"],["status","w1-status","opus","dormant"]]'
  state init --title "Renamed" >/dev/null
  assert_eq "$(jq -r .run.title "$s")" "Renamed"
}

case_plan_import() {
  fresh_home; init_run; state init >/dev/null
  state plan-import "$GOLDEN/plan.md" >/dev/null
  local s="$BOSS_HOME/runs/w1/state.json"
  assert_eq "$(jq -c '[.phases[] | [.id,.title]]' "$s")" '[["P0","Preflight"],["P1","Ingest"],["P2","Wrap"]]'
  assert_eq "$(jq -c '[.phases[].tests[] | .id]' "$s")" '["P0.1","P0.2","T1.1","T1.2","T1.3","T2.1"]'
  assert_eq "$(jq -c '[.phases[].tests[] | .state] | unique' "$s")" '["pending"]'
  assert_eq "$(jq -c '.phases[1].tests[1] | [.owner,.title]' "$s")" '["tester","Duplicate offers are rejected"]'
  assert_file "$BOSS_HOME/runs/w1/plan.md"
  # a verdict survives re-import; re-import is idempotent
  apply_lines "TEST T1.2 PASS — ok" >/dev/null
  state plan-import "$GOLDEN/plan.md" >/dev/null
  assert_eq "$(jq -c '[.phases[].tests[] | .id]' "$s")" '["P0.1","P0.2","T1.1","T1.2","T1.3","T2.1"]' "no duplicates"
  assert_eq "$(jq -r '.phases[1].tests[1] | .state + "|" + .evidence' "$s")" "pass|ok" "verdict kept"
}

case_apply_golden() {
  fresh_home; init_run; state init >/dev/null
  state plan-import "$GOLDEN/plan.md" >/dev/null
  local out
  out="$(state apply "$GOLDEN/feed.txt")"
  assert_eq "$(printf '%s\n' "$out" | sed -n 1p)" "applied: 21" "applied count first"
  assert_eq "$(printf '%s\n' "$out" | sed -n 2p)" "ambiguous: TEST T1.2 BOGUS"
  assert_file "$GOLDEN/state.json"
  local diff_out
  if ! diff_out="$(diff <(jq -S . "$GOLDEN/state.json") <(jq -S . "$BOSS_HOME/runs/w1/state.json"))"; then
    printf '%s\n' "$diff_out" >&2
    fail "state.json differs from golden"
  fi
}

case_apply_malformed_only_goes_to_ambiguous() {
  fresh_home; init_run; state init >/dev/null
  state plan-import "$GOLDEN/plan.md" >/dev/null
  local before after out
  before="$(state_json | jq -S 'del(.version,.ambiguous)')"
  out="$(apply_lines "TEST T1.1 MAYBE — nope")"
  after="$(state_json | jq -S 'del(.version,.ambiguous)')"
  assert_eq "$out" $'applied: 0\nambiguous: TEST T1.1 MAYBE — nope'
  assert_eq "$after" "$before" "no other state change"
  assert_eq "$(state_json | jq -c .ambiguous)" '["TEST T1.1 MAYBE — nope"]'
  assert_eq "$(state_json | jq -r .version)" "2"
  # next apply replaces the ambiguous list
  apply_lines "LOG 10:01 fine" >/dev/null
  assert_eq "$(state_json | jq -c .ambiguous)" '[]'
}

case_mood_derivation() {
  fresh_home; init_run; state init >/dev/null
  assert_eq "$(state_json | jq -r .mood)" "idle" "nothing -> idle"
  apply_lines "TEAM dev ACTIVE — coding" >/dev/null
  assert_eq "$(state_json | jq -r .mood)" "testing" "active team -> testing"
  apply_lines 'DEFECT D1 open major "boom" owner dev' >/dev/null
  assert_eq "$(state_json | jq -r .mood)" "bug-found" "open defect -> bug-found"
  apply_lines "DEFECT D1 fix-pushed abc1234" >/dev/null
  assert_eq "$(state_json | jq -r .mood)" "fixing" "fix-pushed -> fixing"
  apply_lines "DEFECT D1 verified" "TEAM dev DORMANT — done" >/dev/null
  assert_eq "$(state_json | jq -r .mood)" "idle" "verified + dormant -> idle"
  apply_lines "TEST T1.1 RUNNING" >/dev/null
  assert_eq "$(state_json | jq -r .mood)" "testing" "running test -> testing"
  apply_lines 'OWNER tester NEEDS "docker compose up" — held' >/dev/null
  assert_eq "$(state_json | jq -r .mood)" "bug-found" "owner call -> bug-found"
  apply_lines "OWNER tester CLEAR" "OUTCOME GO — ship it" >/dev/null
  assert_eq "$(state_json | jq -r .mood)" "all-green" "GO -> all-green"
  apply_lines "MOOD fixing" >/dev/null
  assert_eq "$(state_json | jq -r '.mood + "|" + .mood_override')" "fixing|fixing" "override honoured"
  apply_lines "MOOD auto" >/dev/null
  assert_eq "$(state_json | jq -r '.mood + "|" + (.mood_override|tostring)')" "all-green|null" "auto clears override"
}

case_owner_needs_then_clear() {
  fresh_home; init_run; state init >/dev/null
  apply_lines 'OWNER tester NEEDS "docker compose up -d" — permission prompt held in tester' >/dev/null
  assert_eq "$(state_json | jq -c '.owner_calls')" '[{"role":"tester","command":"docker compose up -d","why":"permission prompt held in tester","since":"10:00"}]'
  apply_lines 'OWNER tester NEEDS "docker compose down" — again' >/dev/null
  assert_eq "$(state_json | jq -c '[.owner_calls[] | .command]')" '["docker compose down"]' "dedupe by role"
  apply_lines 'OWNER dev NEEDS "git push" — held' "OWNER tester CLEAR" >/dev/null
  assert_eq "$(state_json | jq -c '[.owner_calls[] | .role]')" '["dev"]' "clear removes only that role"
}

case_apply_unplanned_and_unknown_tests() {
  fresh_home; init_run; state init >/dev/null
  apply_lines "TEST V1.2 PASS — surprise" >/dev/null
  assert_eq "$(state_json | jq -c '[.phases[] | [.id,.title,[.tests[].id]]]')" '[["PX","Unplanned",["V1.2"]]]'
  assert_eq "$(state_json | jq -r '.phases[0].tests[0] | .state + "|" + .evidence + "|" + .updated')" "pass|surprise|10:00"
}

case_apply_header_and_log_and_remaining() {
  fresh_home; init_run; state init >/dev/null
  apply_lines 'HEADER branch=feat/x pr="#12 open" title="New title"' >/dev/null
  assert_eq "$(state_json | jq -c '[.header.branch,.header.pr,.run.title]')" '["feat/x","#12 open","New title"]'
  apply_lines "LOG 09:00 first" "LOG second" >/dev/null
  assert_eq "$(state_json | jq -c .log)" '[{"time":"10:00","text":"second"},{"time":"09:00","text":"first"}]' "log prepends"
  apply_lines "REMAINING two things" >/dev/null
  assert_eq "$(state_json | jq -r .remaining)" "two things"
  apply_lines "REMAINING -" >/dev/null
  assert_eq "$(state_json | jq -r .remaining)" "null"
  out="$(apply_lines "HEADER bogus=1")"
  assert_eq "$out" $'applied: 0\nambiguous: HEADER bogus=1' "unknown header key is ambiguous"
}

case_apply_done_and_summary() {
  fresh_home; init_run; state init >/dev/null
  apply_lines "DEFECT D1 open major \"x\" owner dev" >/dev/null
  apply_lines "DONE Fixed the last-field bug; gate green; merged." "SUMMARY did Added failing test, fixed split.sh" "SUMMARY challenge Tester prompt held 6 min" "SUMMARY followup Add CI job" "SUMMARY did Merged 1a2b3c4" >/dev/null
  assert_eq "$(state_json | jq -r .done.headline)" "Fixed the last-field bug; gate green; merged."
  assert_eq "$(state_json | jq -r .done.at)" "10:00" "done stamps now"
  assert_eq "$(state_json | jq -c .summary)" '{"did":["Added failing test, fixed split.sh","Merged 1a2b3c4"],"challenges":["Tester prompt held 6 min"],"followups":["Add CI job"]}'
  assert_eq "$(state_json | jq -r .mood)" "all-green" "DONE forces all-green even with an open defect"
  apply_lines "SUMMARY clear" >/dev/null
  assert_eq "$(state_json | jq -c .summary)" '{"did":[],"challenges":[],"followups":[]}'
  apply_lines "DONE -" >/dev/null
  assert_eq "$(state_json | jq -r .done)" "null"
  assert_eq "$(state_json | jq -r .mood)" "bug-found" "clearing DONE returns to derived mood"
  out="$(apply_lines "SUMMARY bogus text")"
  assert_eq "$out" $'applied: 0\nambiguous: SUMMARY bogus text' "unknown summary kind is ambiguous"
}

case_state_show() {
  fresh_home; init_run; state init >/dev/null
  state plan-import "$GOLDEN/plan.md" >/dev/null
  state apply "$GOLDEN/feed.txt" >/dev/null
  local out
  out="$(state show)"
  echo "$out" | grep -q "version" || fail "show has version"
  echo "$out" | grep -q "D1" || fail "show lists open defects"
  echo "$out" | grep -q "fixing" || fail "show has mood"
}

case_render_fallback() {
  fresh_home; init_run; state init >/dev/null
  say --from boss --to dev --re RUN --subject "hello </script> world" </dev/null >/dev/null
  apply_lines "LOG 09:00 hi" >/dev/null
  local out
  out="$(bash "$SCRIPTS/boss-render" 2>&1)"
  local sp="$BOSS_HOME/runs/w1/pages/status.html" cp="$BOSS_HOME/runs/w1/pages/conversation.html"
  assert_file "$sp"; assert_file "$cp"
  for p in "$sp" "$cp"; do
    assert_contains "$p" '<title>W1 ingest</title>'
    assert_contains "$p" '<script id="boss-run" type="application/json">{"id":"w1"'
    assert_contains "$p" '<script id="boss-state" type="application/json">{'
  done
  assert_contains "$cp" '<script id="boss-conversation" type="application/json">[{"id":"M1"'
  assert_contains "$cp" 'hello <\/script> world'
  # islands round-trip as JSON
  python3 - "$sp" "$cp" <<'PY'
import json, re, sys
for p in sys.argv[1:]:
    html = open(p).read()
    for island in re.findall(r'<script id="boss-[a-z]+" type="application/json">(.*?)</script>', html, re.S):
        json.loads(island)
PY
}

case_render_uses_template_dir() {
  fresh_home; init_run; state init >/dev/null
  local tdir="$REPO/skills/boss-status/templates"
  local made=0
  if [ ! -d "$tdir" ]; then mkdir -p "$tdir"; made=1; fi
  if [ ! -f "$tdir/status-page.html" ]; then
    cat > "$tdir/status-page.html" <<'EOF'
<!doctype html><html><head><title>TEMPLATE</title></head><body>
<div id="marker-status">CUSTOM</div>
<script id="boss-run" type="application/json">{}</script>
<script id="boss-state" type="application/json">{}</script>
</body></html>
EOF
    made=1
  fi
  bash "$SCRIPTS/boss-render" >/dev/null 2>&1
  if [ "$made" = 1 ]; then
    assert_contains "$BOSS_HOME/runs/w1/pages/status.html" 'CUSTOM'
    rm -f "$tdir/status-page.html"; rmdir "$tdir" 2>/dev/null || true; rmdir "$REPO/skills/boss-status" 2>/dev/null || true
  fi
  assert_contains "$BOSS_HOME/runs/w1/pages/status.html" '<title>W1 ingest</title>'
}

# ---------------------------------------------------------------- runner

cases=(
  case_run_init_creates_tree
  case_run_init_refuses_overwrite
  case_run_init_custom_roles
  case_run_set_page
  case_run_close_marks_closed
  case_say_assigns_sequential_ids
  case_say_stdout_golden
  case_say_rejects_invalid
  case_say_parallel_unique_ids
  case_state_init
  case_plan_import
  case_apply_golden
  case_apply_malformed_only_goes_to_ambiguous
  case_mood_derivation
  case_owner_needs_then_clear
  case_apply_unplanned_and_unknown_tests
  case_apply_header_and_log_and_remaining
  case_apply_done_and_summary
  case_state_show
  case_render_fallback
  case_render_uses_template_dir
)

if [ $# -gt 0 ]; then cases=("$@"); fi

for c in "${cases[@]}"; do
  set +e
  ( set -e; "$c" )
  rc=$?
  set -e
  if [ "$rc" -eq 0 ]; then
    echo "PASS $c"; pass_count=$((pass_count + 1))
  else
    echo "FAIL $c"; fail_count=$((fail_count + 1)); failures+=("$c")
  fi
done

echo
echo "tests: $((pass_count + fail_count)) passed: $pass_count failed: $fail_count"
[ "$fail_count" -eq 0 ]
