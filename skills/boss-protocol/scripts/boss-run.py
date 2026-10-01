#!/usr/bin/env python3
"""boss-run: create, inspect and close a boss run directory (protocol.md §1).

  boss-run init <id> [--title T] [--repo P] [--branch B] [--tz IANA] [--role role=session=model ...] [--force]
  boss-run close [<id>]
  boss-run show [<id>]
  boss-run set-page status|conversation <url> [--run <id>]
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.realpath(__file__)))
import _boss  # noqa: E402

DEFAULT_ROLES = [("boss", "fable"), ("dev", "opus"), ("tester", "sonnet"), ("status", "opus")]


def parse_role(spec: str, run_id: str) -> dict:
    parts = spec.split("=")
    if len(parts) != 3 or not all(parts):
        _boss.die(f"--role must be role=session=model, got {spec!r}")
    return {"role": parts[0], "session": parts[1], "model": parts[2]}


def cmd_init(a) -> int:
    home = _boss.boss_home()
    rdir = os.path.join(home, "runs", a.id)
    run_json = os.path.join(rdir, "run.json")
    if os.path.exists(run_json) and not a.force:
        _boss.die(f"run {a.id!r} already exists at {rdir} (use --force to overwrite)", 1)
    tz = a.tz or _boss.system_tz_name()
    roles = [parse_role(r, a.id) for r in a.role] if a.role else [
        {"role": role, "session": f"{a.id}-{role}", "model": model} for role, model in DEFAULT_ROLES
    ]
    for sub in ("evidence", "pages"):
        os.makedirs(os.path.join(rdir, sub), exist_ok=True)
    run = {
        "id": a.id,
        "title": a.title or a.id,
        "repo": os.path.abspath(a.repo) if a.repo else None,
        "branch": a.branch,
        "tz": tz,
        "started": _boss.today(tz),
        "tools_dir": os.path.dirname(os.path.realpath(__file__)),
        "roles": roles,
        "pages": {},
    }
    _boss.write_json(run_json, run)
    with open(os.path.join(rdir, "conversation.jsonl"), "w"):
        pass  # empty, append-only from here on
    os.makedirs(home, exist_ok=True)
    with open(os.path.join(home, "current"), "w") as f:
        f.write(a.id + "\n")
    print(f"initialised run {a.id} at {rdir}")
    print(f'tools_dir: {run["tools_dir"]}')
    return 0


def cmd_close(a) -> int:
    rdir, run = _boss.load_run(a.id)
    run["closed"] = _boss.iso_ts(run["tz"])
    _boss.write_json(os.path.join(rdir, "run.json"), run)
    print(f"run {run['id']} closed at {run['closed']}")
    print()
    print("wrap checklist:")
    print("  [ ] deferred defects each have owner sign-off (deferred is the owner's call)")
    print("  [ ] OUTCOME GO|NO-GO is on the status page (boss-state apply, then boss-render + publish)")
    print("  [ ] memory updated with what this run taught")
    print("  [ ] sessions can be closed: " + ", ".join(r["session"] for r in run.get("roles", [])))
    print()
    print(f"run dir: {rdir}")
    return 0


def cmd_show(a) -> int:
    _, run = _boss.load_run(a.id)
    print(_boss.compact_json(run) if a.compact else __import__("json").dumps(run, indent=2, ensure_ascii=False))
    return 0


def cmd_set_page(a) -> int:
    rdir, run = _boss.load_run(a.run)
    run.setdefault("pages", {})[a.page] = a.url
    _boss.write_json(os.path.join(rdir, "run.json"), run)
    print(f"pages.{a.page} = {a.url}")
    return 0


def cmd_register(a) -> int:
    rdir, run = _boss.load_run(a.run)
    roles = run.setdefault("roles", [])
    row = next((r for r in roles if r.get("role") == a.role), None)
    if row is None:
        row = {"role": a.role, "session": f"{run['id']}-{a.role}", "model": None}
        roles.append(row)
    row["session_id"] = a.session_id
    if a.transcript:
        row["transcript"] = a.transcript
    if a.window:
        row["window"] = a.window
    _boss.write_json(os.path.join(rdir, "run.json"), run)
    print(f"registered {a.role} -> session {a.session_id}")
    return 0


def cmd_resume(a) -> int:
    """One-screen re-orientation for a role after its context was compacted (or on a fresh start)."""
    import json as _json
    rdir, run = _boss.load_run(a.run)
    role = a.role
    st = None
    sp = os.path.join(rdir, "state.json")
    if os.path.exists(sp):
        st = _boss.load_json(sp)
    recs = []
    cp = os.path.join(rdir, "conversation.jsonl")
    if os.path.exists(cp):
        with open(cp, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        recs.append(_json.loads(line))
                    except _json.JSONDecodeError:
                        pass
    hdr = (st or {}).get("header") or {}
    print(f"run {run['id']} — {run.get('title') or ''}   repo {run.get('repo')}   branch {run.get('branch')}")
    print(f"tools_dir {run.get('tools_dir')}   milestone {hdr.get('milestone') or '-'}   page {((run.get('pages') or {}).get('status')) or '-'}")
    if st:
        tests = [t for ph in st.get("phases", []) for t in ph.get("tests", [])]
        counts = {}
        for t in tests:
            counts[t.get("state")] = counts.get(t.get("state"), 0) + 1
        open_d = [d for d in st.get("defects", []) if d.get("status") in ("open", "fixing", "fix-pushed")]
        print(f"tests {len(tests)}: " + ", ".join(f"{k} {v}" for k, v in sorted(counts.items())) + f"   open defects {len(open_d)}: " + ", ".join(d['id'] for d in open_d))
        calls = st.get("owner_calls") or []
        if calls:
            print("owner calls: " + "; ".join(f"{c.get('role')} needs {c.get('command')}" for c in calls))
    mine_in = [r for r in recs if r.get("to") == role][-a.last:]
    mine_out = [r for r in recs if r.get("from") == role][-a.last:]
    print(f"\nlast {len(mine_in)} received by {role}:")
    for r in mine_in:
        print(f"  [{r.get('id')} {r.get('from')}→{r.get('to')} re:{r.get('re')}] {r.get('subject')}")
    print(f"last {len(mine_out)} sent by {role}:")
    for r in mine_out:
        print(f"  [{r.get('id')} {r.get('from')}→{r.get('to')} re:{r.get('re')}] {r.get('subject')}")
    if mine_in and a.body:
        last = mine_in[-1]
        print(f"\n--- body of {last.get('id')} ---\n{last.get('body') or ''}")
    print(f"\nre-read: {os.path.join(os.path.dirname(run.get('tools_dir') or ''), 'protocol.md')} and your role charter; continue from the latest brief above.")
    return 0


def main(argv) -> int:
    p = argparse.ArgumentParser(prog="boss-run", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("init")
    s.add_argument("id")
    s.add_argument("--title")
    s.add_argument("--repo")
    s.add_argument("--branch")
    s.add_argument("--tz")
    s.add_argument("--role", action="append", metavar="role=session=model")
    s.add_argument("--force", action="store_true")
    s.set_defaults(fn=cmd_init)

    s = sub.add_parser("close")
    s.add_argument("id", nargs="?")
    s.set_defaults(fn=cmd_close)

    s = sub.add_parser("show")
    s.add_argument("id", nargs="?")
    s.add_argument("--compact", action="store_true")
    s.set_defaults(fn=cmd_show)

    s = sub.add_parser("register", help="record a role's Claude Code session id so boss-ctx can read its context usage")
    s.add_argument("role")
    s.add_argument("--session-id", required=True)
    s.add_argument("--transcript")
    s.add_argument("--window", type=int)
    s.add_argument("--run")
    s.set_defaults(fn=cmd_register)

    s = sub.add_parser("resume", help="re-orient a role after compaction: run facts, counts, its last messages")
    s.add_argument("role")
    s.add_argument("--last", type=int, default=3)
    s.add_argument("--body", action="store_true", help="also print the body of the latest message received")
    s.add_argument("--run")
    s.set_defaults(fn=cmd_resume)

    s = sub.add_parser("set-page")
    s.add_argument("page", choices=["status", "conversation"])
    s.add_argument("url")
    s.add_argument("--run")
    s.set_defaults(fn=cmd_set_page)

    a = p.parse_args(argv)
    return a.fn(a)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
