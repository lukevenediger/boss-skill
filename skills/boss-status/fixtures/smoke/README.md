# Smoke fixtures for the boss-status templates

`run.json`, `state.json` and `conversation.jsonl` follow protocol.md §1, §3 and §5 and exercise every section of both templates (owner call, open + verified defect, running/fail/pending tests, reply nesting, evidence fence, table, owner message).
The real renderer is `bash skills/boss-protocol/scripts/boss-render` (built in parallel); it replaces the inner JSON of the `boss-run`, `boss-state` and `boss-conversation` islands in `../../templates/*.html`.
For a standalone check without the renderer, run `bash skills/boss-status/fixtures/smoke/preview.sh` (needs python3) and open `/tmp/boss-preview/status.html` and `/tmp/boss-preview/conversation.html`.
Toggle `data-theme="dark"` / `"light"` on `<html>` to check both themes.
`BOSS_PREVIEW_STATE=fixtures/smoke/state-done.json bash preview.sh` renders the closed-run variant (done banner + summary).
