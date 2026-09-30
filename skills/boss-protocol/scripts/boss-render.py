#!/usr/bin/env python3
"""boss-render: fill the JSON islands of the status and conversation templates (protocol.md §6).

  boss-render [--run <id>]

Templates live in <scripts>/../../boss-status/templates/. Each carries
  <script id="boss-run" type="application/json">…</script>
  <script id="boss-state" type="application/json">…</script>
  <script id="boss-conversation" type="application/json">…</script>   (conversation page)
and a <title>. Output: pages/status.html and pages/conversation.html in the run dir.
When a template is missing a minimal built-in page with the same islands is used and a warning printed.
"""
import argparse
import html
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.realpath(__file__)))
import _boss  # noqa: E402

PAGES = [("status-page.html", "status.html"), ("conversation-page.html", "conversation.html")]

FALLBACK = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>boss run</title>
<style>
 body{font:14px/1.5 -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;margin:0;padding:16px;background:#fff;color:#111}
 pre{white-space:pre-wrap;word-break:break-word;background:#f4f4f4;padding:12px;border-radius:6px}
 @media (prefers-color-scheme:dark){body{background:#111;color:#eee}pre{background:#222}}
</style>
</head>
<body>
<h1 id="h"></h1>
<p><em>Fallback page: the real template was not found when this was rendered.</em></p>
<h2>run</h2><pre id="o-run"></pre>
<h2>state</h2><pre id="o-state"></pre>
<h2>conversation</h2><pre id="o-conv"></pre>
<script id="boss-run" type="application/json">{}</script>
<script id="boss-state" type="application/json">{}</script>
<script id="boss-conversation" type="application/json">[]</script>
<script>
(function(){
  function get(id){var el=document.getElementById(id);try{return JSON.parse(el.textContent)}catch(e){return null}}
  var run=get('boss-run')||{};document.getElementById('h').textContent=run.title||run.id||'boss run';
  document.getElementById('o-run').textContent=JSON.stringify(run,null,1);
  document.getElementById('o-state').textContent=JSON.stringify(get('boss-state'),null,1);
  document.getElementById('o-conv').textContent=JSON.stringify(get('boss-conversation'),null,1);
})();
</script>
</body>
</html>
"""


def island_json(data) -> str:
    # `</` inside a <script> would end the element early; `<\/` is the same JSON string.
    return _boss.compact_json(data).replace("</", "<\\/")


def fill_island(page: str, island: str, data) -> str:
    pat = re.compile(rf'(<script\s+id="{island}"[^>]*>)(.*?)(</script>)', re.S)
    if not pat.search(page):
        return page
    payload = island_json(data)
    return pat.sub(lambda m: m.group(1) + payload + m.group(3), page, count=1)


def fill_title(page: str, title: str) -> str:
    return re.sub(r"<title>.*?</title>", lambda m: f"<title>{html.escape(title)}</title>", page, count=1, flags=re.S)


def read_conversation(path: str) -> list:
    out = []
    if not os.path.exists(path):
        return out
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                sys.stderr.write(f"warning: skipping unparsable conversation line: {line[:80]}\n")
    return out


def main(argv) -> int:
    p = argparse.ArgumentParser(prog="boss-render", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--run")
    a = p.parse_args(argv)

    rdir, run = _boss.load_run(a.run)
    state_path = os.path.join(rdir, "state.json")
    state = _boss.load_json(state_path) if os.path.exists(state_path) else None
    if state is None:
        sys.stderr.write("warning: no state.json yet (run boss-state init); rendering an empty state\n")
        state = {}
    conversation = read_conversation(os.path.join(rdir, "conversation.jsonl"))

    scripts_dir = os.path.dirname(os.path.realpath(__file__))
    tdir = os.path.realpath(os.path.join(scripts_dir, "..", "..", "boss-status", "templates"))
    pages_dir = os.path.join(rdir, "pages")
    os.makedirs(pages_dir, exist_ok=True)
    title = run.get("title") or run.get("id") or "boss run"

    for tname, outname in PAGES:
        tpath = os.path.join(tdir, tname)
        if os.path.exists(tpath):
            with open(tpath, encoding="utf-8") as f:
                page = f.read()
        else:
            sys.stderr.write(f"warning: template {tpath} not found; using built-in fallback\n")
            page = FALLBACK
        page = fill_title(page, title)
        page = fill_island(page, "boss-run", run)
        page = fill_island(page, "boss-state", state)
        page = fill_island(page, "boss-conversation", conversation)
        out = os.path.join(pages_dir, outname)
        tmp = f"{out}.tmp.{os.getpid()}"
        with open(tmp, "w", encoding="utf-8") as f:
            f.write(page)
        os.replace(tmp, out)
        print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
