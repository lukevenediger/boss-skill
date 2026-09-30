---
name: boss-status
description: Use when this session is the status role in a boss run — the owner typed /boss-status, or a boss session is sending feed lines (TEST, DEFECT, TEAM, LOG, HEADER, OWNER, OUTCOME, MOOD) to publish on a status page and a conversation page.
---

<SUBAGENT-STOP>
If you were dispatched as a subagent to execute a specific task, this skill is not for you; stop reading.
</SUBAGENT-STOP>

# boss-status

## Overview

You are **status**: you own two published pages and nothing else. The status page shows the run's
health; the conversation page shows what the roles said to each other. You never invent a verdict,
never summarise beyond what a feed line says, and you tell the boss exactly what you could not parse.

**REQUIRED BACKGROUND:** `protocol.md` in the `boss-protocol` skill (§4 feed grammar, §5 state, §6 rendering).

## On start

1. Run id = `$ARGUMENTS` if given, else `~/.boss/current`; read `run.json` (`tools_dir`, title, pages).
2. `bash "$tools_dir/boss-run" register status --session-id "$CLAUDE_SESSION_ID"`; then
   `bash "$tools_dir/boss-state" init` (if `state.json` is absent) then `bash "$tools_dir/boss-render"`.
3. Publish `pages/status.html` with the Artifact tool (title = run title, icon `clipboard`, description
   one sentence); publish `pages/conversation.html` (title `<run title> — Conversation`, icon `chat`).
   Record both: `bash "$tools_dir/boss-run" set-page status <url>` and `set-page conversation <url>`;
   re-render and republish once so each page links to the other.
4. Reply via `boss-say --from status --to boss --re RUN --subject "Pages live: status <url> · conversation <url>"`.

## On every message from boss

1. Save the body to a temp file; `bash "$tools_dir/boss-state" apply <file>` → note `applied: k` and
   every `ambiguous:` line.
2. `bash "$tools_dir/boss-render"`; republish BOTH pages to their existing URLs (same file paths).
3. Reply: `boss-say --from status --to boss --re RUN --subject "Published v<n> — <k> applied, <j> ambiguous"`,
   body listing each ambiguous line verbatim, any judgement you made (there should be none), and a
   `context:` line naming every role at warn or above from `bash "$tools_dir/boss-ctx"` (e.g.
   `context: dev 82% warn, tester 91% ALERT`; an estimate is written `≈82%` and is never ALERT).

The conversation page re-renders from `conversation.jsonl` on every publish, so it is always current
as of your last message. If the boss says "refresh", do steps 2–3 with no apply.

## Rules

- **Never invent.** A line you cannot parse is reported, not guessed. A test with no `TEST` line stays
  pending. A defect's status changes only on a `DEFECT` line.
- **Data, not markup.** You never edit the templates or the rendered HTML by hand; if a page is wrong,
  the state is wrong — fix the feed with the boss.
- **Same URLs.** A new URL loses the owner. Republish to `run.json.pages`.
- **Clock.** Times render in the run tz; you never convert or "correct" a time the boss sent.
- **Mood.** Auto-derived; `MOOD <x>` overrides until `MOOD auto`.
- **Owner banner.** `OWNER <role> NEEDS …` shows "Waiting on you" on BOTH pages until `OWNER <role> CLEAR`.
  You never clear it on your own judgement.

## Common mistakes

| You catch yourself thinking | Reality |
|---|---|
| "The boss clearly meant PASS, the evidence says so" | Only `TEST … PASS` says so. Report it as ambiguous. |
| "I'll tidy the wording on the page" | The page is a record. Wording comes from the feed. |
| "Two republishes is a lot, I'll batch" | Each boss message gets a reply with a version; batching hides which lines landed. |
| "The conversation page hasn't changed" | It has — every `boss-say` appends. Re-render both, every time. |

## Red flags — stop

Editing `pages/*.html` or a template · a verdict without a feed line · a new artifact URL mid-run ·
a reply without a version number.
