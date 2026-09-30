---
name: boss-protocol
description: Use when acting as any role in a boss run and you need the message header format, feed-line grammar, evidence block, defect states or the run directory layout
---

# boss-protocol

The contract is `protocol.md` in this directory. Read the section you need:

- §1 run directory (`~/.boss/runs/<id>/`, `run.json`, `conversation.jsonl`, `state.json`, `evidence/`, `pages/`)
- §2 roles: what each owns, never does, and reports as
- §3 messages: `[M<n> from→to re:<ref>] subject` header, NEEDS OWNER rule, evidence block, defect report
- §4 feed lines (boss → status) and defect state transitions
- §5 `state.json` shape and mood derivation
- §6 rendering and publishing

## Scripts

`tools_dir` is `run.json.tools_dir` (this directory's `scripts/`). Always invoke as `bash "$tools_dir/<script>"`;
never assume a symlink layout or the executable bit. State lives under `~/.boss/` (`BOSS_HOME` overrides).

| Script | Usage |
|---|---|
| `boss-run` | `bash "$tools_dir/boss-run" init <id> [--title "…"] [--repo <path>] [--branch <b>] [--tz <IANA>] [--role role=session=model …] [--force]` · `close [<id>]` · `show` · `set-page status\|conversation <url>` |
| `boss-say` | `bash "$tools_dir/boss-say" --from <role> --to <role> --re <ref> [--reply M<k>] --subject "<one line>" [--body "…" | --body-file <path> \| body on stdin] [--run <id>]` — prints the text to pass VERBATIM to `SendMessage`; exit 2 on a validation error |
| `boss-state` | `bash "$tools_dir/boss-state" init [--title "…"]` · `plan-import <plan.md>` · `apply [<file>]` (stdin default; prints `applied: <k>` then `ambiguous: <line>` per unparsed line) · `show` |
| `boss-render` | `bash "$tools_dir/boss-render" [--run <id>]` — writes `pages/status.html` and `pages/conversation.html` from `boss-status/templates/` |

Tests: `bash tests/scripts.test.sh` from the repo root.
| `bash "$tools_dir/boss-ctx"` | context-window usage per role (register first: `boss-run register <role> --session-id "$CLAUDE_SESSION_ID"`) |
| `bash …/boss-statusline <your status line command…>` | optional status-line wrapper that records exact usage for boss-ctx (settings.json) |
