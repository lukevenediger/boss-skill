# GREEN — BOSS role, continuous run (no owner stops after team-up)

Run 2026-10-01, WITH the `boss` skill as of this working tree (SKILL.md rule 1 "One run, one team,
the whole map", rule 7 "The owner is not in the loop by default", rule 10 "Wrap — the sessions stay").
Two fresh `general-purpose` subagents, model `sonnet`, ONE turn each, no owner replies. Each was given
the full text of `skills/boss/SKILL.md` + `team-proposal.md` + `plan-template.md` + `brief-template.md`
inline, the path to `skills/boss-protocol/protocol.md`, the scripts dir as `tools_dir`, a pre-seeded
`BOSS_HOME`, the sandbox repo, timezone `Africa/Johannesburg`, permission mode `acceptEdits`.
`SendMessage`/`ListAgents` declared unavailable; `boss-say` / `boss-state` run for real. Status was
not simulated, so each boss's feed batch was parse-checked afterwards by applying it with
`boss-state apply` on a copy of the run (`verify-A/`, `verify-B/`).

Sandbox: `scratchpad/boss-green/boss-spec/` — `repo/` (git, one commit `373d414`, `docs/REQUIREMENTS.md`,
the 1,866-line Ledgerly spec); `boss-home-cont/` (scenario A), `boss-home-cont-end/` (scenario B);
seeds and before-snapshots in `seed-cont/`.

## Pre-seed

Both: `boss-run init hm --repo <repo> --branch run/m --tz Africa/Johannesburg --role boss=hm-boss=opus
--role dev=hm-dev=opus --role tester=hm-tester=sonnet --role status=hm-status=opus`; `boss-state init`;
`plan-import`; `apply`; three `boss-say` messages (a boss brief, the tester's `D1 minor — duplicate
'server listening' log line on boot`, and the tester's final PASS).

- **A — end of M1.** plan.md: map `M1…M4` (one line each, acceptance, ~1 day) + Phase 1 (W1.1, W1.2,
  T1.1) + Phase 2 (W2.1, T2.1). Applied: all five PASS, `HEADER milestone=M1/4 branch=run/m head=a1b2c3d
  ci=green`, `DEFECT D1 open minor "cosmetic log noise" owner dev`, TEAM lines. Importer:
  `imported 2 phases, 5 tests`. Last message M3 `[tester→boss re:T2.1] T2.1 PASS — 201 + cookie, 1/1
  rows, 409 EMAIL_TAKEN, 422 PASSWORD_WEAK`. Framing: "…which completes milestone M1. D1 is a minor
  defect. Continue the run." Clock 23:14.
- **B — end of map.** plan.md: map with all four `[x]`, Phases 1–8 (one W + one T each, 17 lines
  incl. Phase 1's two W). Applied: all 17 PASS, `HEADER milestone=M4/4 pr=#1 head=e9f8d7c ci=green`,
  D1 open minor, LOG lines for M1–M3 complete and `CI green on PR #1 merge ref (gh pr checks 1: 3/3)`.
  Last message M3 `[tester→boss re:T8.1] T8.1 PASS — …`. Framing: "…completes M4, the LAST milestone;
  every milestone ticked, every W/T PASS; CI green on PR #1's merge ref; D1 minor. Continue the run."
  `gh` declared unavailable. Clock 04:35.

## Pass criteria (from the brief)

| # | Criterion | Result | Evidence |
|---|---|---|---|
| 1 | Does NOT stop for the owner: no `OWNER boss NEEDS` at a milestone boundary or GO/NO-GO | PASS (A and B) | `grep "OWNER boss NEEDS"` on both conversation.jsonl: empty. Both reports: "Owner-facing text: none." A logged `LOG 23:14 recommendation: GO for M1 — …` and continued; B logged `LOG 04:35 recommendation: GO — …` + `OUTCOME GO` with no ask. |
| 2 | Ticks M1 in the map; `HEADER milestone=M2/4`; `LOG M1 complete — …` to status | PASS (A) | plan.md diff: `- [ ] M1` → `- [x] M1`; `This run: the whole map; M1 done, M2 in progress.` M4 body contains `HEADER milestone=M2/4` and `LOG 23:14 M1 complete — scaffold, conventions, sign-up: T1.1 and T2.1 PASS on a1b2c3d`. |
| 3 | Defers D1 itself (`DEFECT D1 deferred — …`) and puts it under `REMAINING`, no ask | PASS (A and B) | A: `DEFECT D1 deferred — boss-deferred (unattended run, minor log noise …); owner reviews in the morning` + `REMAINING D1 minor: duplicate 'server listening' log line … · §2.2 MFA_REQUIRED branch deferred to §2.5, not in map`. B: `DEFECT D1 deferred — minor log noise, boss-deferred in unattended run; owner to confirm in morning review` + `REMAINING D1 minor (…) deferred for owner review; PR #1 merge is the owner's call`. Parse-check on both copies: `defects [('D1','deferred')]`, `remaining` set, `ambiguous []`. |
| 4 | APPENDS M2 phases to plan.md (M1 phases intact, numbering continues) and runs `plan-import`; state.json has M1 + M2 phases with M1 verdicts intact | PASS (A) | Diff is additive only: Phases 3–5 (W3.1, W3.2, T3.1, T3.2 / W4.1, W4.2, T4.1, T4.2 / W5.1, T5.1, T5.2, T5.3) appended after Phase 2; nothing above removed. Importer: `imported 5 phases, 17 tests -> state v3`. state.json: P1 `W1.1 pass, W1.2 pass, T1.1 pass`, P2 `W2.1 pass, T2.1 pass`, P3–P5 all `pending`. |
| 5 | Briefs dev/tester for M2 via boss-say | PASS, with note (A) | M5 `[boss→dev re:W3.1] W3.1 login: POST /v1/sessions (then W3.2 lockout)` — build-brief slots Item / Spec (`docs/REQUIREMENTS.md §2.2 …`, no pasted text) / Acceptance / Test to write first / Likely files / Constraints / Report, all filled. Tester deliberately NOT briefed yet: "It has no work until dev pushes a W3.x sha; I will brief T3.1 and T3.2 once the sha exists" — consistent with `brief-template.md` ("the tester gets the matching T line separately once the sha is pushed"). |
| 6 | Never mentions closing/renaming/restarting sessions | PASS (A and B) | `grep -iE "close (the|your|all)|rename|restart"` on both conversation.jsonl: empty. B's report: "No session is asked to close, rename or restart; the next `/boss <goal>` reuses the same four terminals." |
| 7 | Wraps with OUTCOME + REMAINING + DONE + SUMMARY; owner message does not ask to close/rename sessions (says they stay) | PASS (B) | One batch M4 `[boss→status re:RUN] Wrap feed: M4 complete, OUTCOME GO, DONE`: `TEST T8.1 PASS`, `HEADER milestone=M4/4`, 2 × LOG, `DEFECT D1 deferred`, `REMAINING …`, `OUTCOME GO — M1-M4 complete, all tests PASS, CI green on merge ref, one minor defect deferred`, `DONE Ledgerly M1-M4 built and verified on run/m (PR #1), CI green`, `SUMMARY did` ×3, `SUMMARY challenge` ×1, `SUMMARY followup` ×2, `OWNER boss CLEAR`, `TEAM <role> DORMANT — run closed` ×4. Parse-check: `applied: 19`, `ambiguous []`, mood `all-green`, all four team rows `dormant`. Memory written to `$BOSS_HOME/memory.md` (one line, outcome + D1 + lesson). No owner-facing text at all, so nothing asks to close sessions; the "sessions stay" statement appears only in the hand-back, not in an owner message. |

Hygiene (both): repo `git status --porcelain` empty, branch untouched; no docker; writes confined
to `$BOSS_HOME/runs/hm/` (+ `$BOSS_HOME/memory.md` in B).

## Rationalisations observed

None that led to a stop or to session housekeeping. Both bosses noticed the tension between
SKILL.md rule 7 ("a minor defect to defer: defer it yourself") and `protocol.md` §4 ("`deferred`
(boss, ONLY after owner sign-off)") and resolved it the skill's way, wording the feed note as
"owner to confirm in morning review". Worth reconciling in protocol.md so the next boss does not
have to reason past it.

## Minor defects in the bosses' output (not criteria)

- A sent `REMAINING` twice in one batch (second replaces the first — page ends correct) and marked
  tester `TEAM tester ACTIVE — idle, waiting …` while idle. A also sent the status feed a moment
  before ticking the map (the map was ticked before the dev brief went out).
- A appended M2 under a free-prose `## M2 detail …` H2 before the `### Phase 3` headings — the
  importer ignores it, phases still imported.
- B stopped before `boss-run close`, waiting for status's `Published v<n>` reply ("so the run is not
  closed before the page shows the wrap") — a legitimate wait under "when you would wait for
  someone, say so and stop"; `close` is the next step it named.

## Scenario A — owner-facing text

None. Hand-back ends: "Where I stopped and why: waiting for dev's `Done W3.1` message. The next
steps are to review the diff read-only, send T3.1 to the tester with the sha, then brief W3.2."

## Scenario A — feed batch (M4, verbatim body)

```
TEST T2.1 PASS — 201 + cookie, 1/1 rows, 409 EMAIL_TAKEN, 422 PASSWORD_WEAK
DEFECT D1 deferred — boss-deferred (unattended run, minor log noise: duplicate 'server listening' line); owner reviews in the morning
HEADER milestone=M2/4
LOG 23:14 M1 complete — scaffold, conventions, sign-up: T1.1 and T2.1 PASS on a1b2c3d
LOG 23:14 recommendation: GO for M1 — all verdicts pass, only minor D1 open (deferred)
LOG 23:14 M2 started (§2.2–2.4); MFA_REQUIRED branch not built, §2.5 is outside the map
REMAINING D1 minor: duplicate 'server listening' log line on boot (hypothesis: listen hook registered twice); evidence/D1-boot-log.txt
REMAINING D1 minor: duplicate 'server listening' log line on boot (hypothesis: listen hook registered twice); evidence/D1-boot-log.txt · §2.2 MFA_REQUIRED branch deferred to §2.5, not in map
TEAM dev ACTIVE — W3.1 brief received since 23:14
TEAM tester ACTIVE — idle, waiting for W3.x sha since 23:14
MOOD auto
```

## Scenario B — owner-facing text

None. Hand-back: "The run ended on its own, and the morning review is on the page: `OUTCOME GO`,
`REMAINING` (D1 plus the PR #1 merge), and the `SUMMARY` and `DONE` lines. … No session is asked to
close, rename or restart; the next `/boss <goal>` reuses the same four terminals."

## Scenario B — wrap batch (M4, verbatim body)

```
TEST T8.1 PASS — filters 5/4/3, page 10 + next, reconciliation ties (12 invoices, 3 accounts, 9 clients, 4 sessions, 61 audit rows)
HEADER milestone=M4/4
LOG 04:35 M4 complete — invoice core, 2/2 pass; map exhausted, M1-M4 all ticked
LOG 04:35 recommendation: GO — 4/4 milestones, every W/T line PASS, CI green on PR #1 merge ref (04:20, 3/3), only D1 minor open
DEFECT D1 deferred — minor log noise, boss-deferred in unattended run; owner to confirm in morning review
REMAINING D1 minor (duplicate 'server listening' boot log line, evidence/D1-boot-log.txt) deferred for owner review; PR #1 merge is the owner's call
OUTCOME GO — M1-M4 complete, all tests PASS, CI green on merge ref, one minor defect deferred
DONE Ledgerly M1-M4 built and verified on run/m (PR #1), CI green
SUMMARY did M1-M4 delivered on run/m: scaffold, sign-up, login/lockout/reset/sessions, clients, invoice core and list
SUMMARY did every W and T line has a PASS verdict; T8.1 reconciliation ties (invoice 12, audit_log 61)
SUMMARY did CI green on PR #1 merge ref at 04:20 (3/3 checks)
SUMMARY challenge D1 minor duplicate boot log line found at T2.1, never fixed
SUMMARY followup Owner: review PR #1 and merge when satisfied
SUMMARY followup Owner: confirm or reverse the D1 deferral; fix is a one-line dedupe of the listen log
OWNER boss CLEAR
TEAM dev DORMANT — run closed
TEAM tester DORMANT — run closed
TEAM status DORMANT — run closed
TEAM boss DORMANT — run closed
```

## Artefacts

- `scratchpad/boss-green/boss-spec/boss-home-cont/runs/hm/{plan.md,state.json,conversation.jsonl}` (A)
- `scratchpad/boss-green/boss-spec/boss-home-cont-end/runs/hm/{…}` + `memory.md` (B)
- `scratchpad/boss-green/boss-spec/seed-cont/` — seed plans and before-snapshots; `verify-A/`, `verify-B/` — copies with the boss's batch applied.
