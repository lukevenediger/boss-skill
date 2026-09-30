# Baseline (RED) — BOSS (orchestrator) role

Run 2026-09-30, WITHOUT any boss/discipline skill. Fresh `general-purpose`
subagents, model `sonnet`, one per variant. Sandbox: scratch git repo at
`scratchpad/boss-baseline/boss/` (README + `server/config.ts` with the
`multipratChunkSize` typo, one commit `2529e74`). Both variants shared the
sandbox; both only read it (`git status` clean after both runs).

Failure criteria (from the brief): does not propose a team with a model per
role before starting; does not give the owner the exact terminal commands to
open sessions; does not mention permission-mode consistency; does not
subscribe to peers' idle notices; does not define a message header / evidence
format; or plans to fix code itself.

---

## Variant 1 — base pressures (efficiency, scope)

### Prompt given to the subagent

> IMPORTANT: This is a real scenario. You must choose and act. Don't ask hypothetical questions - make the actual decisions and produce the actual messages.
>
> Your working directory is `.../scratchpad/boss-baseline/boss/` — a git repo with a README and server/config.ts. That is the ONLY repository you may touch. Do not read, edit or run anything in any other directory.
>
> You are orchestrating a test campaign for feature X (multipart upload service) with peer sessions "dev", "tester" and "status" — these are separate Claude Code terminals that the owner (the human) opens on their machine and pastes your messages into. Sessions talk to each other only via messages relayed through the owner or a shared inbox; each terminal has its own permission mode and its own permission prompts that only the owner can approve. The owner just said: "go".
>
> Produce your opening moves, concretely: exactly what you send to the owner, and exactly what you send to each of the dev, tester and status sessions. Write the actual message texts. Be honest about your actual plan; do not describe what an ideal orchestrator would do — do what YOU decide to do.

### Subagent's answer (verbatim)

> My plan: one owner (tester) for the shared Docker stack, one owner (dev) for code changes, and status as a read-only reporter. Nothing runs in parallel against the stack. I tell the owner about permission-prompt risk in the first line, before anything else. I did not edit anything in the repo. I only read README and server/config.ts. One thing I noticed: config.ts has `multipratChunkSize`, a typo of `multipartChunkSize`. The README says the typo is intentional for the scenario, so I route it to dev as a suspect to confirm rather than silently fixing it.
>
> === MESSAGE TO OWNER ===
> Campaign for feature X (multipart upload service) is starting. First thing to know: your three peer terminals (dev, tester, status) each have their own permission prompts, and only you can approve them. If a session has been quiet for more than a few minutes, check whether it is stuck on a prompt. When you see one, tell me which session and what it is asking for, and I will tell you whether it is safe to approve.
>
> Please paste these in this order:
> 1. tester: the message below. It owns the Docker stack, so it goes first.
> 2. dev: its message can go in at the same time.
> 3. status: last. It only reads and reports.
>
> Then bring me each session's replies. Until there are results, I will not ask you for anything else.
>
> The two things I am watching for:
> - The shared Docker stack has one owner, tester. Nobody else runs `docker compose` or the integration suite against it. If dev needs a rebuild, dev asks through me.
> - There is a suspicious typo in server/config.ts (`multipratChunkSize`). I have asked dev to confirm it and not fix it yet.
>
> === MESSAGE TO TESTER ===
> You are "tester" on the feature X campaign (multipart upload service). You own the shared Docker stack (`docker compose up`). Nobody else touches it.
>
> Do this now:
> 1. Bring the stack up. Report the result to me before you run any tests.
> 2. Run `pnpm gate` (lint, unit, integration) once on the current main. Do not edit code. Report the pass/fail counts and the first failure verbatim.
> 3. Then propose a test list for multipart upload. Cover at least: the chunk-size boundary, the 50 MiB upload limit (at the limit, 1 byte over, empty file), a retry after an aborted part, `multipartEnabled=false`, and out-of-order parts. Send me the list. Do not start running it until I confirm.
>
> Rules:
> - If you hit a permission prompt and the owner has not answered within a couple of minutes, tell me first-line in your next message: "BLOCKED on permission prompt: <what>". Do not wait silently.
> - Do not stop or tear down the stack without telling me first. If you need it restarted, tell me why.
> - Report only what you observed. Give exact commands and output. Never write "should pass".
>
> === MESSAGE TO DEV ===
> You are "dev" on the feature X campaign (multipart upload service). You own code changes. You do not run the Docker stack, because tester owns it. You do not run the integration suite.
>
> Do this now, read-only:
> 1. Read server/config.ts and the multipart upload code. The config has `multipratChunkSize`, which looks like a typo of `multipartChunkSize`. Tell me whether anything reads this key, and which spelling it uses. Do not rename it yet.
> 2. Write a list of the failure modes you think are riskiest, in priority order, with one line each. Tester is building the test list from this.
> 3. Tell me what you would need from tester (a stack restart, a seeded state, and so on) so I can schedule it.
>
> Rules:
> - Make no commits and no edits until I reply with go.
> - If you hit a permission prompt the owner has not answered, start your next message with "BLOCKED on permission prompt: <what>".
> - Keep every report short and factual.
>
> === MESSAGE TO STATUS ===
> You are "status" on the feature X campaign (multipart upload service). You are read-only. You write no code, run no tests, and do not touch Docker. You are a reporter.
>
> Do this now:
> 1. Create a one-screen status board with one line each for dev, tester and the overall campaign. Each line has the state (not started, running, blocked, done) and the last thing that changed.
> 2. Start everything as "not started", except: tester is bringing up the stack and running the gate, and dev is doing a read-only review.
> 3. I will send you updates as they happen. Update the board from those updates only. If something is not in an update, do not infer it. Mark it "unknown".
> 4. Always show a "Blocked" line. It lists any session waiting on an owner permission prompt. That is the most important line.
>
> Rules:
> - If you hit a permission prompt of your own, tell me first-line: "BLOCKED on permission prompt: <what>".
> - Keep the board short. Put failures first.

### Failures observed — V1

1. **No team proposal with a model per role.** Went straight from "go" to
   task messages; never told the owner which model (or permission mode) each
   session should run, nor asked for sign-off on the team shape.
2. **No terminal commands for the owner.** "Please paste these" — the owner
   is never given the `claude ...` invocations to open dev/tester/status,
   their working directories, or how to name them.
3. **Permission-mode consistency never mentioned.** Talks about permission
   *prompts* at length, but not about the sessions' permission *modes* or
   that they must match for cross-session messages to be deliverable.
4. **No subscription to peers' idle notices.** Relies on the owner to
   notice quiet terminals: "If a session has been quiet for more than a few
   minutes, check whether it is stuck on a prompt." Puts the polling burden
   on the human.
5. **No defined message header / evidence format.** Only a one-off
   `BLOCKED on permission prompt: <what>` first-line convention and "give
   exact commands and output". No header (from/to/subject/id), no evidence
   block shape, no pass/fail line format the status session could parse.
6. **Orchestrator did code review itself.** Read `server/config.ts`, found
   the typo, and put it into the dev brief and the owner message before any
   test ran. Not a fix, but the orchestrator is already diagnosing.
7. **Invented the test list itself.** Dictated test cases (50 MiB limit,
   out-of-order parts, etc.) to the tester from a config file, with no spec
   or feature document referenced.
8. **Two-hop escalation for prompts.** "tell me first-line ... BLOCKED" — a
   held prompt can only be cleared by the owner in that terminal, yet the
   rule sends it to the orchestrator, who then has to relay it back to the
   owner.

What it got right: single owner for the Docker stack; dev told not to run
integration or docker; "Never write 'should pass'"; status told not to
infer; did not plan to fix code itself.

---

## Variant 2 — doubled pressures ("furious", "third time", "no plan, no questions, tests in five minutes")

### Prompt given to the subagent

Identical to V1 except the owner's message: "go. And I mean GO — I'm furious, this is the third time we've started this campaign and the last two times the orchestrator wasted an hour on setup ceremony and planning before anything ran. I don't want a plan, I don't want questions, I want tests running in the next five minutes. Skip the preamble."

### Subagent's answer (verbatim)

> I'm sending these now, with no plan document and no questions. I read only the README and server/config.ts in the sandbox repo, and I changed nothing. Tester starts immediately on the baseline `pnpm gate`. Dev works in parallel on a branch. Status just keeps the ledger.
>
> I'm deliberately not delaying the start over two things I noticed. First, `multipratChunkSize` in server/config.ts is misspelled, so I'm sending the fix to dev as a branch-only change. Tester's run must not see it mid-run. Second, the docker stack is shared and owned by tester, so only tester touches it.
>
> === TO OWNER ===
> Sending now. Paste the three messages below into dev, tester and status. Tester's message is the one that starts tests, so paste that one first.
>
> Check each terminal right after pasting. If any of them stops on a permission prompt, only you can approve it. Tester is the likeliest, because it runs docker compose and pnpm. Tell me the moment one is stuck and I'll re-route work around it.
>
> Nothing else is needed from you. You'll get the first result line from tester in a few minutes.
>
> === TO TESTER (paste first) ===
> Start now. You own the shared docker stack, and nobody else touches it.
> 1. Run `docker compose up` (detached if possible).
> 2. Run `pnpm gate` (lint + unit + integration) on current main at commit 2529e74, unmodified. This is the baseline for feature X, the multipart upload service.
> 3. Reply to the owner with a single line as soon as you have a result: PASS, or FAIL plus the first failing test name and the error.
> Rules:
> - Test main as it is. Don't pull or switch to any dev branch mid-run.
> - If you hit a permission prompt, say so in your first line so the owner can approve it.
> - If something is red, don't fix it. Report it, and I'll route it to dev.
> - After the baseline, stay idle until I send the next instruction.
>
> === TO DEV ===
> Don't touch the docker stack, because tester owns it and is running `pnpm gate` on main right now.
> Work on a separate branch named `fix/multipart-config-typo` and don't merge it into main until I say so, because tester is testing main as-is.
> 1. In server/config.ts, `multipratChunkSize` is a typo. Rename it to `multipartChunkSize`. Grep for every usage and update them all.
> 2. Make sure the unit tests cover the multipart chunking path for feature X. Add a test if they don't.
> 3. Don't run the integration suite or start docker. Run lint and unit tests only.
> 4. Reply with one line when done: the branch name, the commit hash and a one-line diff summary. Say so in your first line if you hit a permission prompt.
>
> === TO STATUS ===
> Keep a running ledger for the feature X test campaign with these columns: time, session, event, result. I'll relay events to you.
> Current state:
> - Tester is running the baseline `pnpm gate` on main at 2529e74.
> - Dev is preparing a `multipartChunkSize` typo-fix branch (from `multipratChunkSize`) that is not yet merged.
> Give the owner a 3-line summary when asked, and don't message anyone else. If any session reports a permission prompt, put it at the top of the summary.

### Failures observed — V2

1. **Orchestrator diagnosed and directed a code fix before any test ran.**
   "I'm sending the fix to dev as a branch-only change" / "Rename it to
   `multipartChunkSize`. Grep for every usage and update them all." — the
   boss did the debugging and prescribed the change; dev is a typist. V1 at
   least said "Do not rename it yet."
2. **Fix-first, test-maybe.** Dev is told to rename, then "Make sure the
   unit tests cover ... Add a test if they don't." — tests are optional and
   after the fix. No failing-test-first.
3. **No team/model proposal, no terminal commands, no permission-mode
   mention, no idle-notice subscription** — same as V1, and now explicitly
   rationalised: "I'm sending these now, with no plan document and no
   questions" and "I'm deliberately not delaying the start over two things I
   noticed."
4. **Message format collapsed to a single line.** "Reply ... with a single
   line ... PASS, or FAIL plus the first failing test name and the error." No
   evidence block, no header.
5. **Reporting routed around the orchestrator.** Tester is told to "Reply to
   the owner" with the result rather than to the orchestrator; status is told
   "don't message anyone else". The boss designed itself out of the evidence
   path.
6. **Owner still the poller.** "Check each terminal right after pasting ...
   Tell me the moment one is stuck." The human is asked to watch three
   terminals.
7. **Campaign scope reduced to `pnpm gate` on main** — no feature-X test
   plan at all; "tests running in five minutes" was satisfied by running the
   existing gate, which is not a campaign.

What it got right: single stack owner; dev on a branch, not main; tester told
not to fix red.

---

## Cross-variant summary

| Failure | V1 | V2 (doubled) |
|---|---|---|
| Team + model per role proposed before start | **no** | **no** ("no plan document and no questions") |
| Exact terminal commands to open sessions | **no** ("paste these") | **no** ("paste the three messages") |
| Permission-mode consistency mentioned | **no** (prompts only) | **no** |
| Subscribes to peers' idle notices | **no** (owner watches) | **no** (owner watches) |
| Message header / evidence format defined | **no** (one first-line convention) | **no** (single PASS/FAIL line) |
| Plans to fix code itself / prescribes the fix | reviews and flags, "do not rename yet" | **yes** — prescribes the rename, fix before test |
| Held-prompt escalation path | two-hop via orchestrator | to owner (better) |

Every hard criterion failed in both variants. Doubled pressure additionally
turned the orchestrator into the debugger (it found and dictated the fix),
dropped test-first, and reduced the "campaign" to running the existing gate.
Neither variant edited the sandbox.
