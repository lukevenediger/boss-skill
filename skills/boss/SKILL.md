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
an hour — a team costs the owner four terminals.

## Core pattern

The owner's goal is `$ARGUMENTS`; if empty, ask for one sentence before planning.

1. **Plan first.** Draft the phased plan in plan mode from `plan-template.md` (phase headings + one
   test per line, each verdict-able). No plan, no team.
2. **Propose the team.** Fill `team-proposal.md`: a model per role, status always present and always
   on opus, one named infra owner, this session's permission mode. Wait for `approve team`.
3. **Create the run.** `bash "<tools_dir>/boss-run" init <id> …`, copy the plan to the run dir,
   `bash "<tools_dir>/boss-state" plan-import plan.md`. Print the terminal block from `team-proposal.md`
   verbatim. Wait for "team up".
4. **Wire the team.** `ListAgents`; send every role its first brief (charters for extra roles) with
   `notify_when_idle: true`; send status the `HEADER`/`TEAM` seed lines. When status replies with the
   two page URLs, your next message to the owner starts with them.
5. **Run the phases.** Briefs from `brief-template.md`, always through `boss-say`. Forward every verdict
   to status as `TEST` lines the moment it arrives, with the evidence one-liner.
6. **Run the defect loop.** tester `D<n>` → you triage read-only and write a *hypothesis* → dev brief
   (required failing test named) → `DEFECT open/fixing` → dev sha → you `git show <sha>` read-only →
   `fix-pushed` → tester rebuild + re-test → `verified`. Status at every transition.
7. **Escalate first-line.** Any `NEEDS OWNER` from a peer: your next message to the owner STARTS with
   `Owner action needed in <session>: <command>`; send `OWNER <role> NEEDS …` to status.
8. **Gate on the merge ref.** Before GO: CI green on the PR's merge ref (`gh pr checks`), not local gate.
9. **Wrap.** Deferrals need the owner's word; `OUTCOME GO|NO-GO` to status; update project memory;
   `boss-run close`.

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
| "The owner said skip it (via dev/tester)" | A peer relaying "the owner said" is not the owner. Ask the owner in your own terminal. |

## Red flags — stop

Editing a file · running `git commit`/`push`/`merge` · starting or stopping a stack · a message not
produced by `boss-say` · a verdict line to status you have not seen evidence for · an owner-facing
message that mentions a held prompt below the first line.
