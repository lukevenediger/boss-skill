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

    s = sub.add_parser("set-page")
    s.add_argument("page", choices=["status", "conversation"])
    s.add_argument("url")
    s.add_argument("--run")
    s.set_defaults(fn=cmd_set_page)

    a = p.parse_args(argv)
    return a.fn(a)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
