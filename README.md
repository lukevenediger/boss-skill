# boss

**Run a piece of work as a small team of Claude Code sessions, and follow it from a live page.**

You open four terminals. One is the *boss*: it plans the work, proposes a team, briefs the others,
reviews every change, and decides when it's done. A *dev* fixes things. A *tester* runs things and
collects evidence. A *status* session publishes two pages you can open on your phone: a status
tracker and a threaded log of everything the sessions said to each other.

You stay the owner. The team stops and asks whenever it needs your decision, and the page tells you
so in a banner you cannot miss.

<p align="center">
  <img src="docs/images/status-waiting-on-you.jpg" width="820" alt="Status page mid-run: a red 'Waiting on you' banner, an amber 'Context nearly full' banner, the pet in bug-found mood, progress bar">
</p>

## Why

Letting one Claude session do everything means it edits, tests and judges its own work in one
context window, and you only see what it chooses to tell you. Splitting the work across sessions with
strict roles gives you:

- **Separation of hands.** The session that edits code never touches the test stack; the session that
  runs tests never edits code; the one that decides never does either.
- **Evidence you can check.** Every verdict comes with the command, its exit code and its output.
- **A record.** Every message between sessions is numbered and kept, and rendered as a conversation
  page with threads per test and per defect.
- **No silent stalls.** A session held on a permission prompt tells the boss immediately, and the
  boss puts it on the first line to you. The page shows a banner until you act.
- **No silent forgetting.** Each session's context usage is on the page; when one is nearly full the
  page tells you which terminal to `/compact` in before it loses the plot.

## Install

Requirements: Claude Code CLI 2.1 or later, macOS or Linux, `python3` (3.10+), `bash`, `git`.
Enough screen for four terminals.

```bash
git clone https://github.com/lukevenediger/boss-skill ~/boss-skill
bash ~/boss-skill/install.sh
```

`install.sh` symlinks each skill under `skills/` into `~/.claude/skills`, so the clone is the source
of truth and `git pull` updates it in place. Start a new Claude Code session; `/boss` now appears in
the skill list.

To remove: `bash ~/boss-skill/install.sh --uninstall`.

> Do not also install this repo as a Claude Code plugin. Both installs would trigger at once.

## Use it

### 1. Start the boss

In the repo you want worked on:

```
claude
/rename myrun-boss
/boss fix the CSV splitter so `split.sh a,b,c` keeps the last field, and prove it with the gate
```

Say what "done" looks like in one sentence. The boss drafts a short phased plan (you'll see it in
plan mode) and then shows a **team proposal**: a table of roles, one model per role, who owns the
shared infrastructure, and which permission mode every terminal must use. Reply:

```
approve team
```

(or say what to change: drop the tester for a docs-only run, add a reviewer, use a different model).

### 2. Open the other terminals

The boss prints a block like this:

```
Open these terminals, in the same permission mode as this one (auto):

Terminal 2 (dev):     cd /path/to/repo && claude --model opus     then  /rename myrun-dev     then  /boss-dev myrun
Terminal 3 (tester):  cd /path/to/repo && claude --model sonnet   then  /rename myrun-tester  then  /boss-tester myrun
Terminal 4 (status):  cd /path/to/repo && claude --model opus     then  /rename myrun-status  then  /boss-status myrun

Say "team up" here when all three prompts are idle.
```

Open them exactly as printed. Each session announces itself to the boss. When all three prompts are
idle, tell the boss:

```
team up
```

### 3. Follow along

The boss's next message gives you two links: the **status page** and the **conversation page**. Open
them anywhere. From here the team runs on its own: the boss briefs, the tester reports verdicts with
evidence, defects get numbered, the dev fixes them test-first, the boss reviews each change and sends
the tester back to re-verify, and the pages update after every step.

Watch for two things:

- **"Waiting on you"** at the top of either page. The run is blocked until you answer in the named
  terminal, whether that's a permission prompt, an approval, or a GO / NO-GO decision.
- **Defects** moving `open → fixing → fix-pushed → verified` on the board.

### 4. Wrap up

The boss asks you to sign off anything it wants to defer, writes GO or NO-GO, and closes the run
with a summary. The status page ends like this:

<p align="center">
  <img src="docs/images/status-run-complete.jpg" width="820" alt="Status page after the run: a green 'Run complete' banner and a three-column summary of what was done, challenges and follow-ups">
</p>

You can close all four terminals. Everything the run produced stays under `~/.boss/runs/<run-id>/`:
the plan, the full conversation log, every piece of evidence, and the rendered pages.

## The conversation page

Every message between sessions is numbered (`M1`, `M2`, …), threaded by what it's about (a test id,
a defect id, or the run itself), and rendered newest-first with markdown, collapsible evidence, and a
gold badge for your own decisions.

<p align="center">
  <img src="docs/images/conversation.jpg" width="820" alt="Conversation page: thread rail on the left, numbered messages with role badges, a red-outlined NEEDS OWNER message">
</p>

## Use cases

**A test campaign before a merge.** "Test the new ingestion feature end to end on the local stack
using the real supplier files in `./samples`, fix what breaks, and tell me if it's safe to merge."
The boss writes a phased plan (preflight, happy path, edge cases, idempotency, permissions, reconciliation),
the tester works through it with evidence, the dev fixes defects test-first, and you get a GO / NO-GO
with the reasoning on one page. This is the run the skill was built from: 34 tests, 8 defects, all
verified, one afternoon.

**A bug-fix loop with independent verification.** "Users report `/export` returns 500 for accounts
with no orders. Reproduce, fix, and prove it." The tester reproduces and files D1 with the exact
request and response; the dev writes the failing test, fixes it, pushes; the boss reviews the diff;
the tester re-runs the original repro against the rebuilt service. Nobody grades their own homework.

**A release gate or migration rehearsal.** "Rehearse the database migration on a copy of last night's
snapshot: time each step, confirm the app comes up, and list anything that would need a maintenance
window." Add a `perf` or `dba` role through the proposal; the boss writes it a charter and it reports
like any other session.

**Building from a large spec.** `/boss plan docs/REQUIREMENTS.md — build this` on a 2000-line
document does not produce a 2000-line plan. The boss reads the spec, writes a *milestone map* (M1…Mn,
one line each, about a day of work apiece), asks which milestone to run, and plans only that one as
work items (`W1.1 dev: …`, citing the spec section) with tests to prove them. One run per milestone;
the next run picks up from the map.

**Anything where you want a paper trail.** The conversation log is the audit: who ran what, what it
returned, who decided what, and when.

## The roles

| Role | Owns | Never |
|---|---|---|
| **boss** | the plan, briefs, read-only review of every change, triage, go/no-go, the status feed | edits the repo, runs git writes, touches the stack |
| **dev** | the checkout and branch: failing test → fix → gate → commit → push | the shared stack, force-push |
| **tester** | the shared stack; running exactly what the brief says; evidence; defect reports | editing or committing anything |
| **status** | the two published pages | anything else; inventing a verdict |
| **extra roles** | whatever the boss's charter says (`/boss-role <name> <run-id>`) | whatever it forbids |

Models are proposed per run. Status always runs on the latest Opus. The boss runs on whatever model
your session uses.

## Things to know

- **Same permission mode everywhere.** If one terminal runs in a different mode, messages between
  sessions get held for approval and the run stalls silently. The boss prints the mode; match it.
- **Session names matter.** `/rename <run-id>-<role>` is how the sessions find each other.
- **Runtime lives in `~/.boss/`**, never in your repo. Delete a run directory when you're done with it.
- **The boss will ask.** It stops for `approve team`, `team up`, deferrals, and GO / NO-GO. That's by
  design; the page shows a banner each time.
- **Compact when told.** When the page says a session's context is nearly full, run `/compact` in
  that terminal. The session keeps its name and picks up from the run directory.
- **Pages are private artifacts** on claude.ai. Share them from the page's Share menu if colleagues
  should see them.

## Context windows

Each session's context fills up over a long run; when one compacts mid-task it loses its judgement.
The status page shows a small context meter on every team row and an amber **"Context nearly full"**
banner (default 90%) telling you which terminal to `/compact` in. The session name survives
compaction, so the team carries on.

<p align="center">
  <img src="docs/images/team-context-meters.jpg" width="820" alt="Team panel: each session row shows its activity, state chip and a context meter; dev is red at 92%, tester amber at 78%">
</p>

Readings come from the session transcripts by default (an estimate). For exact numbers, wire the
shipped wrapper into your status line, keeping whatever command you already have after it:

```json
"statusLine": { "type": "command", "command": "bash ~/boss-skill/skills/boss-protocol/scripts/boss-statusline <your existing command>" }
```

## Layout

| Path | What |
|---|---|
| `skills/boss/` | orchestrator skill; templates for the team proposal, plan, briefs and role charters |
| `skills/boss-dev/`, `boss-tester/`, `boss-status/`, `boss-role/` | one charter per role |
| `skills/boss-protocol/` | `protocol.md` (the contract every role follows) and the scripts `boss-run`, `boss-say`, `boss-state`, `boss-render` |
| `skills/boss-status/templates/` | the two pages, rendered from JSON |
| `tests/` | script tests, pressure-test transcripts for each charter, a toy repo for a full dry run |

## Try it without risking anything

```bash
bash ~/boss-skill/tests/toy-repo.sh          # builds /tmp/boss-toy with one planted bug
cd /tmp/boss-toy && claude
/rename toy-boss
/boss fix the last-field bug in lib/split.sh and prove it with the gate
```

## Developing the skill

```bash
bash tests/scripts.test.sh                        # 21 golden tests for the scripts
bash skills/boss-status/fixtures/smoke/preview.sh # renders both pages from a fixture into /tmp/boss-preview
```

Charters were written test-first: `tests/scenarios/baseline-*.md` records what fresh sessions did
*without* each charter, `green-*.md` what they did with it. Change a charter the same way.

## License

MIT.
