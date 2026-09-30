# tests

- `bash tests/scripts.test.sh` — golden tests for the four protocol scripts (temp `BOSS_HOME` per case).
- `scenarios/baseline-*.md` — RED: what fresh agents did WITHOUT each charter (verbatim rationalisations).
- `scenarios/green-*.md` — GREEN: the same scenarios WITH the charter; new rationalisations feed the
  charters' "Common mistakes" tables.
- `bash tests/toy-repo.sh` — builds `/tmp/boss-toy` with one planted bug for a full mini-run:
  open four terminals per the README, `/boss fix the last-field bug in lib/split.sh and prove it with
  the gate`, and watch D1 go open → fixing → fix-pushed → verified on the page.
- `skills/boss-status/fixtures/smoke/preview.sh` — renders both pages from a fixture into `/tmp/boss-preview`.

Skill edits follow superpowers:writing-skills: change a charter only after a scenario shows the failure
without it, and re-run the scenario with it.
