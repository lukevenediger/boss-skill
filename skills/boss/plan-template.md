# Plan template

The boss writes the plan in plan mode before proposing the team, then copies it to
`~/.boss/runs/<id>/plan.md` after `boss-run init`. `boss-state plan-import` reads ONLY the phase
headings and test lines below, so keep their shape exact; everything else is free prose.

```markdown
# <run-id> — <goal in one line>

## Context
Why this work exists, what "done" means, what is out of scope. Three to eight sentences.

## Roles and protocol
Roles per the approved team proposal. Shared-infra owner: <role>. All timestamps <tz>.
Every brief carries: goal · exact commands · expected result · evidence to capture · report-as.
Tester reports `T<id> PASS|FAIL|BLOCKED` + evidence block; defects `D<n>` with severity, repro,
expected vs actual. Dev replies with sha + test file. Boss reviews every diff read-only before re-test.

## Phases

### Phase 0 — Preflight
- P0.1 dev: gate green on HEAD <sha>
- P0.2 tester: stack up, health probes, migration state, tables empty

### Phase 1 — <title>
- T1.1 tester: <one-line test, with the expected outcome in the line>
- T1.2 tester: …

### Phase N — Wrap
- PN.1 boss: every defect verified, or deferred with owner sign-off
- PN.2 boss: OUTCOME GO|NO-GO on the status page with evidence summary
- PN.3 boss: memory updated with what the run taught us

## Defect workflow
tester `D<n>` → boss triage + root-cause hypothesis → dev failing test → fix → gate → push sha →
boss `git show` review → tester rebuild (content-hash check) + re-test → `verified`.
Status updated at every transition. Boss checks CI on the merge ref before GO.

## Run is complete when
Every test has a verdict · no open blocker/major · reconciliation ties · CI green on the merge ref ·
owner has the go/no-go.
```

## Build work: milestone map + work items

For work driven by a document, the plan file starts with a milestone map and then details ONE milestone:

```markdown
## Milestones (from docs/REQUIREMENTS.md)
- [ ] M1 Accounts: sign-up, login, password reset — acceptance: §2.1–2.4 flows pass e2e — ~1 day
- [ ] M2 Catalogue read API — acceptance: §3 endpoints return fixtures with contract tests — ~1 day
- [ ] M3 …
This run: M1.

### Phase 1 — Sign-up (§2.1)
- W1.1 dev: POST /accounts creates a user; duplicate email → 409 (§2.1.3); contract test
- W1.2 dev: verification email job enqueued on create (§2.1.5); unit test on the job payload
- T1.1 tester: sign-up e2e against the stack: 201, row present, one job in the queue
```

`W<n>.<m>` lines are work items (owner dev); `T<n>.<m>` lines verify them (owner tester). Every W
line names the spec section and the test that proves it. Later runs tick the map and continue.

## Line shapes the importer reads

- Phase heading: `### Phase <n> — <title>` or `### P<n> — <title>` (em dash or hyphen both accepted).
- Item line: `- <Id> <owner>: <title>` where `<Id>` matches `[A-Z]\d+\.\d+` (`P0.1`, `T2.3`, `W1.2`)
  and `<owner>` is a role name. `W` = work item (dev), `T` = test (tester), `P` = preflight. One test per line. Put the expected outcome IN the title so the page
  reads as a checklist.

## Writing good test lines

- Each line is independently verdict-able by the owner reading the page.
- Prefer counts and exact codes over adjectives: "12 rows / 7 applied / 4 review" beats "works".
- Negative cases get their own line ("wrong adapter → 400 HEADER_NOT_FOUND, nothing written").
- A reconciliation line at the end of every data phase: totals in = totals out, no dangling ids.
