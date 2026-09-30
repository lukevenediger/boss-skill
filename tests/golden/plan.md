# W1 ingest — phased plan

Prose before the first heading is ignored by plan-import.

### Phase 0 — Preflight
- P0.1 dev: Branch builds and gate passes locally
- P0.2 tester: Shared stack up on the run image

### P1 — Ingest
- T1.1 tester: Upload a supplier list
- T1.2 tester: Duplicate offers are rejected
Notes between test lines are ignored too.
- T1.3 tester: Malformed rows are reported, not dropped

### Phase 2 — Wrap
- T2.1 boss: CI green on the merge ref
