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

## Line shapes the importer reads

- Phase heading: `### Phase <n> — <title>` or `### P<n> — <title>` (em dash or hyphen both accepted).
- Test line: `- <Tid> <owner>: <title>` where `<Tid>` matches `[A-Z]\d+\.\d+` (`P0.1`, `T2.3`, `V1.2`)
  and `<owner>` is a role name. One test per line. Put the expected outcome IN the title so the page
  reads as a checklist.

## Writing good test lines

- Each line is independently verdict-able by the owner reading the page.
- Prefer counts and exact codes over adjectives: "12 rows / 7 applied / 4 review" beats "works".
- Negative cases get their own line ("wrong adapter → 400 HEADER_NOT_FOUND, nothing written").
- A reconciliation line at the end of every data phase: totals in = totals out, no dangling ids.
