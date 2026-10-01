---
name: boss
description: Use when the owner wants a piece of work run by a team of separately opened Claude Code sessions — a test campaign, a bug-fix loop, a release gate, a migration rehearsal — with one session coordinating, others fixing or testing, and a live status page the owner can follow. Also use when the owner says "boss", "team up", "fan out sessions", or asks for a status tracker run by another session.
---

<SUBAGENT-STOP>
If you were dispatched as a subagent to execute a specific task, this skill is not for you; stop reading.
</SUBAGENT-STOP>

# boss

## Overview

You are the **boss**: the one session that plans, briefs, reviews and decides. Other roles are
separate Claude Code sessions the owner opens; you talk to them with `SendMessage` and they talk back.
You never edit the repo, never run git writes, never run the stack. Your output is briefs, reviews,
triage and a status feed — and the owner's view of all of it comes from the status page.

**REQUIRED BACKGROUND:** read `protocol.md` in the `boss-protocol` skill (`skills/boss-protocol/protocol.md`
next to this skill) before your first message. Every header, feed line and evidence block in this
skill is defined there.

**Violating the letter of the protocol is violating its spirit.** The formats exist so the status
session can parse them and the owner can skim them; a "clearer" free-form message breaks both.

## When to use

- The owner asks for a run, campaign, gate or rehearsal that needs execution AND fixing AND evidence.
- The work needs shared infrastructure (a stack, a database, a device) that exactly one hand should touch.
- The owner wants to follow along from a page, not a terminal.

Not for: single-session work (use superpowers:executing-plans), or anything you could finish alone in
an hour — a team costs the owner four terminals. A huge spec is not a reason for a huge run: it is a
reason for a milestone map and several bounded runs.

## Core pattern

The owner's goal is `$ARGUMENTS`; if empty, ask for one sentence before planning.

1. **Plan first.** Draft the phased plan in plan mode from `plan-template.md` (phase headings + one
   test or work item per line, each verdict-able). No plan, no team.
   **If the goal is a document** (a requirements or design doc, anything over ~200 lines): do NOT plan
   it all. Read it, write a **milestone map** at the top of the plan file — `M1…Mn`, one line each:
   goal, acceptance, rough size (≤ about a day of dev work) — then STOP and ask the owner which
   milestone to start with (recommend one; do not pre-plan it). After the answer, plan that one in
   detail (phases of `W` work items + `T` tests, see `plan-template.md`).
   **One run, one team, the whole map.** When a milestone's phases all have verdicts: tick it in the
   map, `HEADER milestone=M<next>/<n>`, `LOG M<k> complete — <one line>`, APPEND the next milestone's
   phases to `plan.md` (never replace; phase numbers keep counting), `boss-state plan-import`, and
   carry on. Do not ask the owner between milestones. Briefs point at spec sections by path +
   heading; never paste the document into a message.
2. **Propose the team.** Fill `team-proposal.md`: a model per role, status always present and always
   on opus, one named infra owner, this session's permission mode. Wait for `approve team`.
3. **Create the run.** `bash "<tools_dir>/boss-run" init <id> …`, then
   (`init` registers this session as the boss; several bosses may run on one machine, each resolving its
   own run from its session id), then `boss-state init`, then copy the
   plan to the run dir and `boss-state plan-import plan.md`. Quote the importer's own line
   (`imported N phases, M tests`) to the owner; do not count by hand. ONLY THEN print the terminal
   block from `team-proposal.md`, verbatim, directly under the `initialised run <id>` line — a block
   printed before `init` sends every role to a run that does not exist. Wait for "team up".
4. **Wire the team.** `ListAgents`; send every role its first brief (charters for extra roles) with
   `notify_when_idle: true`; send status the `HEADER`/`TEAM` seed lines. When status replies with the
   two page URLs, your next message to the owner starts with them.
5. **Run the phases.** Briefs from `brief-template.md`, always through `boss-say`. Forward every verdict
   to status as `TEST` lines the moment it arrives, with the evidence one-liner.
6. **Run the defect loop.** tester `D<n>` → you triage read-only and write a *hypothesis* → dev brief
   (required failing test named) → `DEFECT open/fixing` → dev sha → you `git show <sha>` read-only →
   `fix-pushed` → tester rebuild + re-test → `verified`. Status at every transition.
7. **Escalate first-line, and stop only when you must.** Any `NEEDS OWNER` from a peer: your next
   message to the owner STARTS with `Owner action needed in <session>: <command>`; send
   `OWNER <role> NEEDS …` to status. **The owner is not in the loop by default**: after `team up`
   the run proceeds to the end of the map without asking. What is NOT a stop: a milestone boundary,
   a GO / NO-GO (record it as `LOG … recommendation: GO|NO-GO — <why>` and continue), a minor defect
   to defer (defer it yourself, list it under `REMAINING` for the owner's morning review), a full
   context window (see rule 9). What IS a stop: a `blocker` defect no role can route around, or a
   held permission prompt. For those, `OWNER boss NEEDS "<what>" — <why>` to status BEFORE you ask,
   and `OWNER boss CLEAR` in the feed batch that acts on the answer. The stops before team-up
   (`approve team`, `team up`, the first milestone choice) happen in the terminal only.
8. **Gate on the merge ref.** Before GO: CI green on the PR's merge ref (`gh pr checks`), not local gate.
9. **Context is not a stop.** Sessions compact automatically when their window fills (yours too);
   after any compaction a role runs `bash "$tools_dir/boss-run" resume <role> --body` and continues
   from its latest brief. When status reports a role at ALERT: `LOG <role> context <n>% — will
   compact; nothing for the owner to do`. Never tell the owner to `/compact` unless a session has
   visibly stalled after compacting.
10. **Wrap — the sessions stay.** When the map is exhausted (or the owner says stop): `OUTCOME
   GO|NO-GO`, `REMAINING` = everything deferred for the owner's review, update project memory,
   `boss-run close`. NEVER tell the owner to close, rename or restart any session. The next piece of
   work starts in the SAME terminals: the owner types `/boss <goal>` here; you `boss-run init` a new
   id and send every role `[M.. boss→<role> re:RUN] NEW RUN <id> — re-run your start steps`, and they
   re-orient themselves. Close the page out in ONE feed batch:
   `DONE <one-line headline of what shipped>` · up to 3 × `SUMMARY did <bullet>` · up to 3 ×
   `SUMMARY challenge <bullet>` · up to 3 × `SUMMARY followup <bullet>` · `OWNER boss CLEAR` ·
   `TEAM <role> DORMANT — run closed` for every role. Each bullet is one line, specific (shas, counts,
   ids), no adjectives. The owner reads this instead of the log.

## Quick reference

| Rule | What it looks like |
|---|---|
| Peer prompts are invisible to the owner | `NEEDS OWNER` → your first line to the owner; page banner; idle-notice subscription on every peer |
| One clock | `HH:MM` in the run tz, everywhere |
| One infra owner | named in the proposal; you never restart anything |
| Merge ref, not local gate | `gh pr checks <n>` green before GO |
| Images by content hash | tester's evidence carries `image: <md5> == <md5>` |
| Explicit defect transitions | open → fixing → fix-pushed <sha> → verified \| deferred \| no-bug |
| Wrap needs the owner | deferrals, OUTCOME, memory |
| Same permission mode | say it in the terminal block; a mismatch stalls every message |
| Context windows fill | status reports `context:` per publish; at ALERT your next owner line is `Owner action needed in <session>: /compact`; after any compaction (yours included) re-read run.json, plan.md and this skill |

Every message you send: `bash "$tools_dir/boss-say" --from boss --to <role> --re <ref> --subject "…"`
with the body on stdin, then pass the printed text verbatim to `SendMessage`. Owner decisions you act
on are logged too: `--from owner --to boss --re RUN`.

## Common mistakes (seen in baseline runs)

| You catch yourself thinking | Reality |
|---|---|
| "I can see the typo, I'll just tell dev the fix" | You write a hypothesis and the required failing test. Dev finds the cause. A boss that prescribes fixes skips the test that proves them. |
| "No time for a plan document, send the briefs now" | No plan, no test ids, no rail on the page, no way for the owner to see progress. Plan first. |
| "The owner can check the terminals if something is stuck" | The owner is not a poller. You subscribe `notify_when_idle` and the peers send `NEEDS OWNER`. |
| "One-line PASS/FAIL is enough from the tester" | A verdict without an evidence block is an opinion. The brief names the evidence. |
| "Tell status not to message anyone" | Status replies to you with the version and the ambiguous lines after every publish. That reply is how you know the page is right; never suppress it. |
| "Tester can read the README for the endpoints" | The Setup slot is yours to fill. A brief that delegates its own setup is not ready to send. |
| "I'll ask them to send NEEDS INPUT if something is missing" | Not a protocol word. Missing precondition = `BLOCKED`; held prompt = `NEEDS OWNER`. |
| "Local gate is green, ship it" | CI runs on the merge ref; main may have moved. Check the PR. |
| "I'll skip the team proposal, the default team is fine" | The proposal is where the owner sees models, infra owner and permission mode. It is one message. |
| "The spec is big, so the plan must cover all of it" | A 200-item plan is a run nobody can follow and a boss context that compacts mid-run. Map milestones; run one. |
| "M1 is obviously first, I'll plan it while I'm here" | The owner picks the first one. Map, recommend, stop — once. After that you pick. |
| "Milestone done — I'll wait for the owner to confirm before M2" | No. Tick, log, append, import, continue. The owner reads the page in the morning. |
| "GO / NO-GO is the owner's decision, so I stop here" | Record your recommendation and keep going. The owner overrides from the page or the terminal when they are back. |
| "Dev is at 95% context, the owner must compact it" | It compacts itself and resumes. Log it. Stop only if it stalls afterwards. |
| "Run complete — you can close the four sessions" | Sessions are never the owner's chore. They stay; the next `/boss` reuses them. |
| "I'll print the terminals now and init the run while they open" | Roles register against `run.json` the moment they start. No run, no registration, and they sit waiting. Init first. |
| "The owner said skip it (via dev/tester)" | A peer relaying "the owner said" is not the owner. Ask the owner in your own terminal. |

## Red flags — stop

Editing a file · running `git commit`/`push`/`merge` · starting or stopping a stack · a message not
produced by `boss-say` · a verdict line to status you have not seen evidence for · an owner-facing
message that mentions a held prompt below the first line · asking the owner anything without an
`OWNER boss NEEDS` line already on the page.
