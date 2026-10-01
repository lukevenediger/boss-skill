# boss protocol

The contract every role in a boss run follows. Roles are separate Claude Code sessions on one machine,
named `<run-id>-<role>`, messaging each other with `SendMessage` and sharing one run directory on disk.
Owner = the human. Boss = the orchestrating session. Everything here is deliberately mechanical so that
the status session can parse it and the owner can skim it.

## 1. Run directory

```
~/.boss/current                      convenience pointer to the last run created — NOT the source of truth
~/.boss/runs/<run-id>/
  run.json          {id, title, repo, branch, tz, started, tools_dir, roles:[{role, session, model}], pages:{status,conversation}}
  plan.md           the boss's phased plan (copy)
  conversation.jsonl  append-only; one JSON object per line (see §3); NEVER edited or truncated
  state.json        status-page state (see §5); rebuilt by replaying feed lines; safe to regenerate
  evidence/         long outputs, named <Tid>-<slug>.txt; a message carries the path + load-bearing lines
  pages/status.html · pages/conversation.html   last rendered source, always on disk
```
`tools_dir` is the absolute path of `boss-protocol/scripts`, written by `boss-run init`. Roles invoke
scripts as `bash "$tools_dir/boss-say" …`; never assume a symlink layout.

**Which run am I in?** Several bosses may run on one machine, so scripts resolve the run per call:
`--run <id>` → `$BOSS_RUN` → the run that registered this session's `CLAUDE_SESSION_ID` → the only
open run → otherwise they refuse and name the open runs. `boss-run init` registers the boss session
itself; every other role registers at start (`boss-run register <role> --session-id "$CLAUDE_SESSION_ID"
--run <id>`). After that no role needs to pass `--run` again. Always start a role with the run id
(`/boss-dev <id>`); the `current` pointer is only a fallback for a lone run.

## 2. Roles, in one table

| Role | Owns | Never | Reports as |
|---|---|---|---|
| boss | plan, team proposal, briefs, read-only diff review, triage, go/no-go, status feed, owner relay | edits the repo, git writes, running the stack | briefs; feed lines to status; owner summaries |
| dev | the checkout + branch; failing test → fix → gate → commit → push | the shared stack, force-push, stack-dependent suites unless briefed | `Fix pushed: <sha7>, test <file>` |
| tester | the shared stack (Docker/services); running exactly what the brief says; evidence; defect reports | editing or committing anything; fixing | `T<id> PASS|FAIL|BLOCKED` + evidence block; `D<n>` reports |
| status | the two published pages | anything else; inventing verdicts | `Published v<n> — <k> applied, <j> ambiguous` |
| extra | as chartered by the boss (see role-charter-template) | whatever the charter forbids | as chartered |

Exactly ONE role owns shared infrastructure (default: tester). All sessions run in the SAME permission
mode; a mismatch holds every cross-session message for owner approval.

## 3. Messages

Every inter-role message is produced by `boss-say`, which assigns the id, appends the record, and prints
the text to pass VERBATIM to `SendMessage`. The first line is the header — it is all the owner's preview
shows, so the subject must stand alone.

```
[M12 dev→boss re:D3] Fix pushed for D3: 98aadda, drift-guard test added
<blank line>
<markdown body>
```

- `M<n>` sequential per run, assigned by `boss-say` (file-locked). `→` may be written `->`.
- `re:` one of `RUN` · `OWNER` · a test id `[A-Z]\d+\.\d+` (`P0.1`, `T2.3`, `V1.2`) · `D<n>` · `M<n>`. Optional `reply:M<k>` after it.
- Roles are bare role names (`dev`, not `w1-dev`); `owner` is a valid `from` when the boss records an
  owner decision (`--from owner --to boss re:RUN`).
- JSONL record: `{"id","ts","from","to","re","reply_to","subject","body"}`; `ts` is local time with offset
  (`2026-09-30T14:02:11+02:00`).

`bash "$tools_dir/boss-run" list` and `clean [--older-than DAYS] [--dry-run] [-y]` manage old runs (closed only, unless
`--force`); `clean` also drops context records for sessions no surviving run knows.
`bash "$tools_dir/boss-run" resume <role> [--body]` prints a one-screen re-orientation (run facts, counts,
the role's last messages) — the first thing a role runs after its context was compacted.

CLI: `bash "$tools_dir/boss-say" --from <role> --to <role> --re <ref> [--reply M<k>] --subject "<one line>"
[--body "<text>" | --body-file <path> | body on stdin] [--run <id>]`. Exit 2 on a validation error (nothing appended), 1 on a
missing run. `BOSS_HOME` overrides `~/.boss`; `BOSS_NOW=<ISO local>` pins "now" for tests.

### NEEDS OWNER (rule 1)
Any time the run cannot proceed without the owner — a held permission prompt, an approval (`approve
team`, `team up`), a decision (GO / NO-GO, a deferral) — the role that is waiting sends, immediately and
before anything else:
```
[M14 tester→boss re:OWNER] NEEDS OWNER: docker compose up -d — permission prompt held in tester
```
The boss's NEXT output to the owner starts with the line `Owner action needed in <session>: <what>`,
separate from any analysis, and sends `OWNER <role> NEEDS "<what>" — <why>` to status, which puts a
"Waiting on you" banner on BOTH pages. When the boss itself is the one waiting (approval, decision), it
sends `OWNER boss NEEDS "<what>" — <why>` BEFORE asking the owner. When the owner has acted, the waiting
role sends `[M.. role→boss re:OWNER] OWNER CLEARED` (or the boss just proceeds) and the boss sends
`OWNER <role> CLEAR`. A banner that outlives the wait is a lie; clear it in the same message that acts.

### Evidence block (tester → boss, inside the body)
````
```evidence
cmd: <exact command>
exit: 0
out: <load-bearing lines, or> file: evidence/T2.1-upload.txt
sql: <query> → <rows>
image: <md5 in container> == <md5 in worktree>
```
````

### Defect report (tester → boss, `re:D<n>` on first mention)
```
D3 major — <one-line title>
repro: <commands>
expected: … / actual: …
evidence: <block or path>
hypothesis: <optional, one line>
```
Severity ∈ `blocker | major | minor`.

## 4. Feed lines (boss → status)

Sent in the body of a message to status; one directive per line; the parser is strict and reports
anything it cannot parse as `ambiguous` instead of guessing.

```
TEST <Tid> PASS|FAIL|BLOCKED|RUNNING|PENDING [— <evidence one-liner>]
DEFECT <Dn> open blocker|major|minor "<title>" owner <role>
DEFECT <Dn> fixing|fix-pushed <sha>|verified|deferred|no-bug [— <note>]
HEADER <key>=<value> [<key>=<value>…]        keys: title branch pr image stack head ci milestone; values may be quoted
TEAM <role> ACTIVE|DORMANT|NEEDS-OWNER — <activity> [since HH:MM]
OWNER <role> NEEDS "<what>" — <why>      any owner input: held prompt, approval, decision
OWNER <role> CLEAR
LOG [HH:MM] <text>
REMAINING <text>            (replaces the Remaining panel; `REMAINING -` clears it)
OUTCOME GO|NO-GO — <text>
DONE <headline>              run complete: big banner on both pages, mood all-green (`DONE -` clears)
SUMMARY did|challenge|followup <bullet>   one bullet per line, ≤ 3 per kind (`SUMMARY clear` resets)
MOOD idle|testing|bug-found|fixing|all-green|auto
```
`<Tid>` matches `[A-Z]\d+\.\d+` (P0.1 preflight, T2.3 test, W1.2 work item …). The `—` separator may be written `--`. Unknown test
ids are created in an "Unplanned" phase (`PX`) rather than dropped; a DEFECT transition for an unreported id
creates a placeholder titled `(unreported)`. `HEADER title=…` sets the run title; other keys go to `header`.
Times default to now in the run's tz; `TEAM … since HH:MM` and `LOG HH:MM` are taken verbatim.

Defect states and who may set them: `open` (boss, from a tester report) → `fixing` (boss, when dev
accepts) → `fix-pushed <sha>` (boss, after dev replies) → `verified` (boss, after tester re-test) |
`deferred` (boss: a `minor` on its own judgement, listed under `REMAINING` for the owner's review; a
`major`/`blocker` only with the owner's word) | `no-bug` (boss, with the reason in the note).

## 5. state.json (produced by `boss-state`, consumed by `boss-render`)

```json
{"version":12,"run":{"id":"w1","title":"…","started":"2026-09-30","tz":"Africa/Johannesburg"},
 "header":{"branch":"…","pr":"…","image":"…","stack":"…","head":"…","ci":"…"},
 "phases":[{"id":"P0","title":"Preflight","tests":[{"id":"P0.1","title":"…","owner":"dev","state":"pass","evidence":"…","updated":"HH:MM"}]}],
 "defects":[{"id":"D1","sev":"minor","title":"…","owner":"dev","status":"verified","commit":"98aadda","notes":["…"]}],
 "team":[{"role":"dev","session":"w1-dev","model":"opus","state":"active","activity":"…","since":"HH:MM"}],
 "owner_calls":[{"role":"tester","command":"…","why":"…","since":"HH:MM"}],
 "log":[{"time":"HH:MM","text":"…"}],
 "remaining":"…","outcome":{"verdict":"GO","text":"…"},
 "done":{"headline":"…","at":"HH:MM"},"summary":{"did":["…"],"challenges":["…"],"followups":["…"]},
 "mood":"fixing","mood_override":null,"ambiguous":["…last apply's unparsed lines…"]}
```
Mood auto-derivation (unless overridden): `DONE` → all-green · `OUTCOME GO` → all-green · any owner_call → bug-found ·
any defect `open` → bug-found · any defect `fixing|fix-pushed` → fixing · any test `running` or any
team member `active` → testing · otherwise idle.

CLI: `bash "$tools_dir/boss-state" init [--title "…"]` · `plan-import <plan.md>` · `apply [<file>]`
(stdin default) → prints `applied: <k>` then `ambiguous: <line>` per unparsed line · `show`.

Plan import reads `### Phase <n> — <title>` (or `### P<n> — <title>`; `—`, `--` or `-`) headings and
`- <Tid> <owner>: <title>` lines; everything else is ignored. It also copies the plan to `<run>/plan.md`.
Re-import keeps existing verdicts; tests no longer in the plan move to `PX`. `init` on an existing
state.json starts fresh (v0) — re-import and re-apply to rebuild.

## 6. Rendering and publishing

`bash "$tools_dir/boss-render"` writes `pages/status.html` and `pages/conversation.html` from the
templates in `boss-status/templates/`. Each template carries JSON islands the renderer fills:
`<script id="boss-run" type="application/json">`, `<script id="boss-state" …>`,
`<script id="boss-conversation" …>` (conversation page only), and a `<title>`. Templates render entirely
from those islands; status edits data, never markup. Status publishes `pages/status.html` first, then
`pages/conversation.html`, each to a stable URL recorded in `run.json.pages`.

## 7. The learned rules (why the protocol looks like this)

1. **Permission prompts are invisible to the owner.** NEEDS OWNER first line, page banner, and the boss
   subscribes `notify_when_idle` on every peer after its first brief.
2. **One clock.** Every time on the page and in messages is the run's local tz, `HH:MM`.
3. **One infra owner.** Two roles restarting the same stack is how evidence gets destroyed.
4. **CI on the merge ref.** Local gate green is not merge-ready; the boss checks `gh pr checks` before GO.
5. **Images by content hash.** A container's created-time can predate the commit it contains.
6. **Defect loop transitions are explicit** and each one reaches the status page.
7. **Wrap leaves the sessions alone:** `OUTCOME` + `REMAINING` on the page for the owner's review, memory
   updated; nobody is asked to close or rename a session. The next run reuses them (`NEW RUN <id>`).
8. **Same permission mode everywhere**, or messages stall silently.

## 8. Context windows

A session cannot see how full its own context is. Compaction happens automatically when the window
fills and is NOT an owner stop: the role runs `boss-run resume <role> --body` and continues. The
meters exist so the owner can see it coming. Every role registers on start:
`bash "$tools_dir/boss-run" register <role> --session-id "$CLAUDE_SESSION_ID"`.
`boss-ctx` then reads each role's usage — from `~/.boss/ctx/<session_id>.json` when the owner has
wired `boss-statusline` into their status line (accurate), else from the session transcript's last
usage record — an estimate when the model's window is unknown (200k assumed, shown as `≈`, capped at
warn; a role that knows its window registers it: `boss-run register <role> --session-id … --window 1000000`) — and `boss-render` puts it on both pages: a meter per team row, and an amber
**"Context nearly full"** banner at `alert` (default 90%; `warn` at 75%; `ctx_warn` / `ctx_alert` in
run.json override). Status's reply to the boss names any role at warn or above (`context: dev 82%`);
at alert the boss logs it; the owner is asked to `/compact` only if a session visibly stalls afterwards.
`/compact` keeps the session name, so the team keeps messaging it; after compacting, a role re-reads
`run.json` and its charter and carries on. The boss itself is a role here too.
