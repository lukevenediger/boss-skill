# boss

Run a piece of work as a **team of separately opened Claude Code sessions**: one *boss* that plans,
briefs and decides; a *dev* that fixes; a *tester* that runs and gathers evidence; a *status* session
that publishes a live status page and a threaded conversation page the owner can follow (and share).

```
┌ Terminal 1 ─ /boss ────────┐   briefs, triage, review     ┌ Terminal 2 ─ /boss-dev ────┐
│ plan → team → run → wrap   │ ───────────────────────────▶ │ failing test → fix → gate  │
│ owner talks here           │ ◀─── "Fix pushed: sha, test" │ → push                     │
└────────────┬───────────────┘                              └────────────────────────────┘
             │ TEST / DEFECT / TEAM / LOG lines             ┌ Terminal 3 ─ /boss-tester ─┐
             ▼                                              │ owns the stack; verdict +  │
┌ Terminal 4 ─ /boss-status ─┐                              │ evidence; defect reports   │
│ status page + conversation │ ◀── every message, via the   └────────────────────────────┘
│ page (published artifacts) │     shared run log
└────────────────────────────┘
```

Every message between roles goes through `boss-say`, which numbers it and appends it to a shared
`conversation.jsonl`; the status session renders that log as a threaded conversation page next to the
status page. A role whose command is held for a permission prompt sends `NEEDS OWNER` first, and the
boss puts it on the first line to the owner — the one thing the previous run taught the hard way.

## Install (this machine)

```
git clone https://github.com/lukevenediger/boss-skill ~/lukevenediger/boss-skill
bash ~/lukevenediger/boss-skill/install.sh          # symlinks skills/* into ~/.claude/skills
```

The repo stays the source of truth; edits are live. Do not also install it as a plugin (the skills
would trigger twice). `install.sh --uninstall` removes the links.

## Use

1. Terminal 1, in the repo: `claude` → `/rename <run-id>-boss` → `/boss <what you want done>`.
2. The boss drafts a phased plan, proposes a team (a model per role; status always on opus) and waits
   for `approve team`.
3. It prints the terminals to open. Open them, in the same permission mode, and say `team up`.
4. Follow the two page links the boss gives you. Act on any "Owner action needed" line.
5. At the end the boss asks you to sign off deferrals and writes GO / NO-GO on the page.

## Layout

| Path | What |
|---|---|
| `skills/boss/` | orchestrator skill + team-proposal, plan, brief and role-charter templates |
| `skills/boss-dev/`, `skills/boss-tester/`, `skills/boss-status/`, `skills/boss-role/` | one charter per role |
| `skills/boss-protocol/` | `protocol.md` (the contract), scripts `boss-run`, `boss-say`, `boss-state`, `boss-render` |
| `skills/boss-status/templates/` | status page + conversation page (data-driven; JSON islands) |
| `tests/` | `scripts.test.sh` (golden tests), `scenarios/` (pressure-test transcripts), `toy-repo.sh` |
| `~/.boss/runs/<id>/` | runtime: run.json, plan.md, conversation.jsonl, state.json, evidence/, pages/ |

## Test

```
bash tests/scripts.test.sh        # scripts against golden files
bash tests/toy-repo.sh            # builds a scratch repo with one planted bug for a full mini-run
```

Skill behaviour was pressure-tested with subagents before and after writing each charter; the
transcripts are in `tests/scenarios/`.

## License

MIT.
