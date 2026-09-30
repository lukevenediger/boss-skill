#!/usr/bin/env python3
"""boss-statusline: record this session's context usage for boss-ctx, then run the real status line.

Wire it in ~/.claude/settings.json, keeping whatever command you already had after it:

  "statusLine": { "type": "command",
                  "command": "bash ~/boss-skill/skills/boss-protocol/scripts/boss-statusline crmux rpc status-update" }

Claude Code pipes its status-line JSON to stdin; this writes $BOSS_HOME/ctx/<session_id>.json
(used_pct, window, tokens, model, session_name, transcript_path, ts) and then execs the chained
command with the SAME stdin, so your existing status line keeps working. With no chained command it
prints a one-line status of its own. Never raises: a failure to record must not break the status line.
"""
import json
import os
import subprocess
import sys
from datetime import datetime, timezone


def record(raw: str) -> str | None:
    try:
        d = json.loads(raw)
    except json.JSONDecodeError:
        return None
    sid = d.get("session_id")
    if not sid:
        return None
    cw = d.get("context_window") or {}
    cu = cw.get("current_usage") or {}
    tokens = None
    if cu:
        tokens = sum(int(cu.get(k) or 0) for k in ("input_tokens", "cache_read_input_tokens", "cache_creation_input_tokens"))
    elif cw.get("total_input_tokens") is not None:
        tokens = int(cw.get("total_input_tokens") or 0)
    model = (d.get("model") or {}).get("id")
    out = {"session_id": sid, "session_name": d.get("session_name"), "used_pct": cw.get("used_percentage"),
           "window": cw.get("context_window_size"), "used_tokens": tokens, "model": model,
           "transcript_path": d.get("transcript_path"), "cwd": d.get("cwd"),
           "ts": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")}
    home = os.environ.get("BOSS_HOME") or os.path.join(os.path.expanduser("~"), ".boss")
    cdir = os.path.join(home, "ctx")
    try:
        os.makedirs(cdir, exist_ok=True)
        tmp = os.path.join(cdir, f".{sid}.{os.getpid()}.tmp")
        with open(tmp, "w") as f:
            json.dump(out, f)
        os.replace(tmp, os.path.join(cdir, f"{sid}.json"))
    except OSError:
        return None
    return f"{d.get('session_name') or sid[:8]} ctx {out['used_pct'] if out['used_pct'] is not None else '?'}%"


def main(argv) -> int:
    raw = sys.stdin.read()
    summary = None
    try:
        summary = record(raw)
    except Exception:  # noqa: BLE001 — the status line must never break because of us
        summary = None
    if argv:
        try:
            r = subprocess.run(argv, input=raw, text=True)
            return r.returncode
        except OSError as e:
            sys.stdout.write(summary or f"status line: {e}")
            return 0
    sys.stdout.write(summary or "")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
