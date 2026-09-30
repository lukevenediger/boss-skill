# Brief template

A brief is what the boss sends a role to start a unit of work. It is produced with `boss-say` so it
gets an M-id and lands in the conversation log. The recipient must be able to act without asking a
question; if you cannot fill a slot, you are not ready to send.

```
bash "$tools_dir/boss-say" --from boss --to tester --re T2.1 --subject "T2.1–T2.4 real supplier lists" <<'EOF'
## Goal
One sentence: what this brief proves or produces.

## Setup (once)
A='--base-url http://localhost:53000 --as @ops --role ops'      # every env/auth prefix defined here, once

## Steps
T2.1 <title>
  cmd: pnpm vice ingest upload --source-id $SRC --file local/timex.xlsx --wait $A --json
  expect: status done, 210 rows / 210 applied / 0 review
  evidence: the --json output; `select status, count(*) from ingest.rows where file_id=$F group by 1`
T2.2 …

## Report
One message per test: `[M.. tester→boss re:T2.1] T2.1 PASS — <one line>` + evidence block in the body.
Defects as `D<n>` in their own message (`re:D<n>`) with severity, repro, expected/actual, evidence.
Long output → evidence/<Tid>-<slug>.txt, message carries the path plus the load-bearing lines.

## Stop conditions
Stop and report immediately if: <a precondition fails> · any command is held for permission
(send NEEDS OWNER first) · <anything destructive would be needed>.
EOF
```

## Slots, in order

| Slot | Must contain |
|---|---|
| Goal | one sentence, outcome not activity |
| Setup | every prefix / env / id the steps use, defined once, BY THE BOSS — never "find it in the README"; ids from earlier steps referenced by name |
| Steps | per test: `cmd` copy-pasteable, `expect` with numbers/codes, `evidence` naming what to capture |
| Report | the exact header shape and `re:` to use; where long output goes |
| Stop conditions | what ends the brief early, and that NEEDS OWNER precedes everything |

## For dev briefs (defects)

Add these slots: **Defect** (`D<n>`, severity, one-line title) · **Repro** (exact) · **Observed** (log
lines / codes verbatim) · **Hypothesis** (boss's read of the root cause, marked as a hypothesis) ·
**Required test** (where the failing test goes and what it asserts) · **Constraints** (what not to
touch; e.g. "do not run the stack-dependent suites") · **Report** (`Fix pushed: <sha7>, test <file>`).

## For build briefs (work items, `re:W<n>.<m>`)

Slots: **Item** (`W<n>.<m>`, one-line title) · **Spec** (path + heading to read, e.g.
`docs/REQUIREMENTS.md §2.1.3` — never the text itself) · **Acceptance** (observable: request → response,
row present, job enqueued) · **Test to write first** (file + what it asserts) · **Likely files** ·
**Constraints** · **Report** (`Done W<n>.<m>: <sha7>, test <file>`). One item per brief; the tester
gets the matching `T` line separately once the sha is pushed.

## Common mistakes

- Expected results described as adjectives ("works", "fine") — give the number or the code.
- Auth/env prefix repeated on every line, or missing on one — define once in Setup.
- A brief that needs the recipient to choose between two readings — decide, or ask the owner first.
- Forgetting the stop conditions; the recipient then either stalls silently or improvises.
- Inventing report keywords ("NEEDS INPUT"). A missing precondition is `T<id> BLOCKED — <what>`; a held
  prompt is `NEEDS OWNER`. Nothing else exists.
- Hedging a decision onto the recipient ("if it needs an edit, ask"). Decide before sending; a tester
  never edits, so a test that needs a config edit is a dev task or an env var.
