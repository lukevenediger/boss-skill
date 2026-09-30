#!/usr/bin/env bash
# Inject the smoke fixtures into both templates and write /tmp/boss-preview/{status,conversation}.html.
# Standalone stand-in for `boss-render`; python3 only, no other dependencies.
set -euo pipefail
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
templates="$here/../../templates"
out="${1:-/tmp/boss-preview}"
mkdir -p "$out"

python3 - "$here" "$templates" "$out" <<'PY'
import json, os, re, sys
fixtures, templates, out = sys.argv[1:4]

def load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)

def load_jsonl(path):
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]

def island(html, island_id, data):
    # JSON inside a <script> must not close the element early; "<\/" is a valid JSON escape.
    payload = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    pattern = re.compile(r'(<script id="%s" type="application/json">)(.*?)(</script>)' % re.escape(island_id), re.S)
    html, n = pattern.subn(lambda m: m.group(1) + payload + m.group(3), html, count=1)
    if n != 1:
        sys.exit("island %s not found" % island_id)
    return html

run = load(f"{fixtures}/run.json")
state = load(os.environ.get("BOSS_PREVIEW_STATE") or f"{fixtures}/state.json")
conv = load_jsonl(f"{fixtures}/conversation.jsonl")

for name, islands in (("status", {"boss-run": run, "boss-state": state}),
                      ("conversation", {"boss-run": run, "boss-state": state, "boss-conversation": conv})):
    with open(f"{templates}/{name}-page.html", encoding="utf-8") as f:
        html = f.read()
    for island_id, data in islands.items():
        html = island(html, island_id, data)
    html = re.sub(r"<title>.*?</title>", "<title>%s</title>" % run["title"].replace("&", "&amp;").replace("<", "&lt;"), html, count=1, flags=re.S)
    with open(f"{out}/{name}.html", "w", encoding="utf-8") as f:
        f.write(html)
    print(f"wrote {out}/{name}.html")
PY
