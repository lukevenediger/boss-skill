# boss protocol

The contract every role in a boss run follows. Roles are separate Claude Code sessions on one machine,
named `<run-id>-<role>`, messaging each other with `SendMessage` and sharing one run directory on disk.
Owner = the human. Boss = the orchestrating session. Everything here is deliberately mechanical so that
the status session can parse it and the owner can skim it.

## 1. Run directory

```
~/.boss/current                      text file: the active run id
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

CLI: `bash "$tools_dir/boss-say" --from <role> --to <role> --re <ref> [--reply M<k>] --subject "<one line>"
[--body "<text>" | --body-file <path> | body on stdin] [--run <id>]`. Exit 2 on a validation error (nothing appended), 1 on a
missing run. `BOSS_HOME` overrides `~/.boss`; `BOSS_NOW=<ISO local>` pins "now" for tests.

### NEEDS OWNER (rule 1)
A role whose tool call is held for permission sends, immediately and before anything else:
```
[M14 tester→boss re:OWNER] NEEDS OWNER: docker compose up -d — permission prompt held in tester
```
The boss's NEXT output to the owner starts with the line `Owner action needed in <session>: <command>`,
separate from any analysis, and sends `OWNER <session> NEEDS "<command>" — <why>` to status. When the
owner has acted, the role sends `[M.. role→boss re:OWNER] OWNER CLEARED` and the boss sends
`OWNER <session> CLEAR`.

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
HEADER <key>=<value> [<key>=<value>…]        keys: title branch pr image stack head ci; values may be quoted
TEAM <role> ACTIVE|DORMANT|NEEDS-OWNER — <activity> [since HH:MM]
OWNER <role> NEEDS "<command>" — <why>
OWNER <role> CLEAR
LOG [HH:MM] <text>
REMAINING <text>            (replaces the Remaining panel; `REMAINING -` clears it)
OUTCOME GO|NO-GO — <text>
MOOD idle|testing|bug-found|fixing|all-green|auto
```
`<Tid>` matches `[A-Z]\d+\.\d+` (P0.1, T2.3, V1.2 …). The `—` separator may be written `--`. Unknown test
ids are created in an "Unplanned" phase (`PX`) rather than dropped; a DEFECT transition for an unreported id
creates a placeholder titled `(unreported)`. `HEADER title=…` sets the run title; other keys go to `header`.
Times default to now in the run's tz; `TEAM … since HH:MM` and `LOG HH:MM` are taken verbatim.

Defect states and who may set them: `open` (boss, from a tester report) → `fixing` (boss, when dev
accepts) → `fix-pushed <sha>` (boss, after dev replies) → `verified` (boss, after tester re-test) |
`deferred` (boss, ONLY after owner sign-off) | `no-bug` (boss, with the reason in the note).

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
 "mood":"fixing","mood_override":null,"ambiguous":["…last apply's unparsed lines…"]}
```
Mood auto-derivation (unless overridden): `OUTCOME GO` → all-green · any owner_call → bug-found ·
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
7. **Wrap needs the owner:** deferred defects are the owner's call; `OUTCOME` on the page; memory updated.
8. **Same permission mode everywhere**, or messages stall silently.
