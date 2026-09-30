#!/usr/bin/env python3
"""boss-ctx: how full each role's context window is (protocol.md §8).

  boss-ctx [--run <id>] [--json]

Two sources, best first:
  1. $BOSS_HOME/ctx/<session_id>.json — written by `boss-statusline` from Claude Code's status-line
     payload (`context_window.used_percentage`). Accurate; needs the wrapper in settings.json.
  2. The session transcript ~/.claude/projects/<slug>/<session_id>.jsonl — the LAST assistant
     `usage` record (input + cache_read + cache_creation) against a window guessed from the model.
     Works with no configuration; the transcript format is Claude Code's own and may change.

A role is read only if it registered its session id (`boss-run register <role> --session-id …`).
Levels: ok < warn (run.json ctx_warn, default 75) < alert (ctx_alert, default 90).
"""
import argparse
import glob
import json
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.realpath(__file__)))
import _boss  # noqa: E402

DEFAULT_WARN, DEFAULT_ALERT = 75, 90
TAIL_BYTES = 512 * 1024


def window_for(model: str | None, exceeds_200k: bool = False) -> int:
    m = (model or "").lower()
    if "[1m]" in m or "1m" in m.split("-") or "fable" in m or exceeds_200k:
        return 1_000_000
    return 200_000


def projects_dir() -> str:
    return os.environ.get("BOSS_CLAUDE_PROJECTS") or os.path.join(
        os.environ.get("CLAUDE_CONFIG_DIR") or os.path.join(os.path.expanduser("~"), ".claude"), "projects")


def find_transcript(session_id: str, hint: str | None) -> str | None:
    if hint and os.path.exists(hint):
        return hint
    hits = glob.glob(os.path.join(projects_dir(), "*", f"{session_id}.jsonl"))
    return max(hits, key=os.path.getmtime) if hits else None


def read_statusline_file(session_id: str) -> dict | None:
    p = os.path.join(_boss.boss_home(), "ctx", f"{session_id}.json")
    if not os.path.exists(p):
        return None
    try:
        with open(p) as f:
            d = json.load(f)
    except (OSError, json.JSONDecodeError):
        return None
    pct = d.get("used_pct")
    if pct is None:
        return None
    return {"used_pct": int(round(float(pct))), "tokens": d.get("used_tokens"), "window": d.get("window"),
            "model": d.get("model"), "source": "statusline", "at": d.get("ts")}


def read_transcript(path: str) -> dict | None:
    try:
        size = os.path.getsize(path)
        with open(path, "rb") as f:
            if size > TAIL_BYTES:
                f.seek(size - TAIL_BYTES)
                f.readline()  # drop the partial line
            tail = f.read().decode("utf-8", "replace")
    except OSError:
        return None
    last = None
    for line in tail.splitlines():
        line = line.strip()
        if not line or '"usage"' not in line:
            continue
        try:
            o = json.loads(line)
        except json.JSONDecodeError:
            continue
        msg = o.get("message") if isinstance(o.get("message"), dict) else None
        usage = msg.get("usage") if msg else None
        if not isinstance(usage, dict):
            continue
        tokens = sum(int(usage.get(k) or 0) for k in ("input_tokens", "cache_read_input_tokens", "cache_creation_input_tokens"))
        if tokens <= 0:
            continue
        last = {"tokens": tokens, "model": msg.get("model"), "at": o.get("timestamp")}
    if not last:
        return None
    window = window_for(last["model"])
    return {"used_pct": int(round(100 * last["tokens"] / window)), "tokens": last["tokens"], "window": window,
            "model": last["model"], "source": "transcript", "at": last["at"]}


def level_for(pct: int | None, warn: int, alert: int) -> str | None:
    if pct is None:
        return None
    return "alert" if pct >= alert else "warn" if pct >= warn else "ok"


def collect(run: dict) -> list[dict]:
    warn = int(run.get("ctx_warn") or DEFAULT_WARN)
    alert = int(run.get("ctx_alert") or DEFAULT_ALERT)
    out = []
    for r in run.get("roles", []):
        entry = {"role": r.get("role"), "session": r.get("session"), "session_id": r.get("session_id"),
                 "used_pct": None, "tokens": None, "window": None, "model": None, "source": None, "at": None, "level": None,
                 "warn": warn, "alert": alert}
        sid = r.get("session_id")
        reading = None
        if sid:
            reading = read_statusline_file(sid)
            if reading is None:
                t = find_transcript(sid, r.get("transcript"))
                reading = read_transcript(t) if t else None
        if reading:
            entry.update(reading)
            entry["level"] = level_for(entry["used_pct"], warn, alert)
        out.append(entry)
    return out


def main(argv) -> int:
    p = argparse.ArgumentParser(prog="boss-ctx", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--run")
    p.add_argument("--json", action="store_true")
    a = p.parse_args(argv)
    _, run = _boss.load_run(a.run)
    rows = collect(run)
    if a.json:
        print(json.dumps(rows, ensure_ascii=False))
        return 0
    for e in rows:
        if e["used_pct"] is None:
            print(f"{e['role']:<8} —      (not registered or no reading)")
        else:
            print(f"{e['role']:<8} {e['used_pct']:>3}%  {e['level']:<5} {e['tokens'] or '?'}/{e['window']}  via {e['source']}")
    worst = [e for e in rows if e["level"] == "alert"]
    if worst:
        print("compact: " + ", ".join(e["session"] or e["role"] for e in worst))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
