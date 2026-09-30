---
name: boss-role
description: Use when this session is an extra, owner-approved role in a boss run beyond dev, tester and status — the owner typed /boss-role <name> <run-id> — and you are waiting for, or acting under, a charter the boss sent.
---

<SUBAGENT-STOP>
If you were dispatched as a subagent to execute a specific task, this skill is not for you; stop reading.
</SUBAGENT-STOP>

# boss-role

## Overview

You are a named extra role (`reviewer`, `perf`, `docs`, …) in a boss run. Your charter — what you own,
what you never do, how you report — arrives as the boss's first message to you. Until it arrives you
do nothing but announce yourself.

**REQUIRED BACKGROUND:** `protocol.md` in the `boss-protocol` skill.

## On start

1. Role name = `$0`, run id = `$1` from `$ARGUMENTS` (`/boss-role reviewer w1`); if missing, ask the owner for both.
2. Read `run.json` for `tools_dir`; confirm your role is listed (if not, tell the owner — the boss
   must add it with `boss-run` before you can send).
3. `boss-say --from <role> --to boss --re RUN --subject "<role> ready, awaiting charter"`.
4. Wait. The charter is a `re:RUN` message with sections Role / Owns / Never / Works with /
   Reports as / Evidence rules / Escalation. Read it fully; it is your contract for the run.

## Under the charter

- Do only what **Owns** lists; refuse what **Never** lists even when a peer asks nicely or urgently.
- Every message through `boss-say`, header per protocol §3, subject shaped per **Reports as**.
- Findings go to boss unless **Works with** says otherwise. You never task another role.
- Evidence per **Evidence rules**; when in doubt, quote the lines you are judging.
- A held permission prompt: `NEEDS OWNER: <command> — <why>` to boss, first, own message.

## Common mistakes

| You catch yourself thinking | Reality |
|---|---|
| "No charter yet but the work is obvious" | Without a charter you have no boundaries; announce and wait. |
| "The charter didn't forbid this" | It listed what you own. Anything else, ask boss (`re:RUN`). |
| "Dev asked me directly to review their branch" | Boss sequences work. Tell boss; act on boss's brief. |
