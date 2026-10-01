# Team proposal

The boss proposes a team for THIS piece of work before anything else happens. The owner approves it
(or edits it) by replying `approve team`. Nothing is briefed, no run directory exists, until then.

## Shape

```
## Team proposal — <run-id>: <one-line goal>

| Role   | Session         | Model  | Owns                                   | Never                              | Why this model |
|--------|-----------------|--------|----------------------------------------|------------------------------------|----------------|
| boss   | <id>-boss       | fable  | plan, briefs, review, triage, go/no-go | repo edits, git writes, the stack  | this session   |
| dev    | <id>-dev        | opus   | checkout, fixes, gate, push            | the stack, force-push              | root-causing needed |
| tester | <id>-tester     | sonnet | the stack, commands, evidence, defects | edits, commits                     | scripted execution |
| status | <id>-status     | opus   | the status + conversation pages        | anything else                      | always opus    |

Shared infrastructure owner: tester. Permission mode for all sessions: <this session's mode>.
Run id: <id>   Repo: <path>   Branch: <branch>   Timezone: <tz>
Attendance: attended (you may be asked about blockers) | unattended (nothing asks; blockers are
logged and routed around, deferrals listed for your review). Default: unattended.
Reply `approve team`, or say what to change.
```

`<run-id>`: short, lowercase, hyphenated, unique on this machine (`w1-test`, `pay-recon-2`).

## Model rules

| Role | Default | Rule |
|---|---|---|
| boss | the model this session runs (fable / opus) | never downgrade the boss |
| dev | opus | opus when the work needs root-causing or design judgement; sonnet only when every fix is handed over as exact code |
| tester | sonnet | haiku only when every command is pre-scripted and no judgement is needed on evidence |
| status | **opus, always** | never any other model; never dropped from the team |
| extra roles | justify each | model chosen by the judgement the role needs, stated in "Why this model" |

Aliases the owner types: `--model fable | opus | sonnet | haiku`.

## Team rules

- Default team is boss / dev / tester / status. Dropping dev or tester needs a stated reason in the
  proposal (e.g. "docs-only run, nothing to fix" → no dev).
- Add a role only when it owns something no default role owns (e.g. `reviewer` for an independent
  code review, `perf` for a load rig). Extra roles use `role-charter-template.md` and the owner starts
  them with `/boss-role <role> <run-id>`.
- Exactly one role owns shared infrastructure. Name it in the proposal.
- Session names are `<run-id>-<role>`; roles inside messages are bare (`dev`).

## After approval — the terminal block

Run `bash "<tools_dir>/boss-run" init <id> --title "…" --repo <path> --branch <b> --role role=session=model …`,
then print exactly this (fill in models from the approved table):

```
Open these terminals, in the same permission mode as this one (<mode>):

Terminal 2 (dev):     cd <repo> && claude --model opus     then  /rename <id>-dev      then  /boss-dev <id>
Terminal 3 (tester):  cd <repo> && claude --model sonnet   then  /rename <id>-tester   then  /boss-tester <id>
Terminal 4 (status):  cd <repo> && claude --model opus     then  /rename <id>-status   then  /boss-status <id>

Say "team up" here when all three prompts are idle.
```

Every terminal starts in the repo, status included (same permission scope, same `.claude` settings).
Extra roles get a line each with `/boss-role <role> <id>`.

**Unattended runs** (overnight, remote): a held permission prompt is the one thing that stalls a
session with nobody there. Add `--permission-prompts none` to every `claude` line in the block; a
denied call then comes back as a refusal the role reports as `BLOCKED` instead of a prompt nobody
answers, and the boss routes around it. Say in the proposal that this is what the block will carry.

**These sessions are reused.** Nothing in this skill ever asks the owner to close, rename or restart
a session. A finished run leaves the four terminals idle; the next `/boss` in the boss terminal
starts a new run in the same sessions.
