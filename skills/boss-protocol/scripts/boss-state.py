#!/usr/bin/env python3
"""boss-state: build state.json by replaying feed lines (protocol.md §4, §5).

  boss-state init [--title "…"] [--run <id>]
  boss-state plan-import <plan.md> [--run <id>]
  boss-state apply [<file>] [--run <id>]      (stdin default)
  boss-state show [--run <id>]

The parser is strict: any line it cannot parse is reported as `ambiguous: <line>` and stored in
state.ambiguous instead of being guessed at.
"""
import argparse
import json
import os
import re
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.realpath(__file__)))
import _boss  # noqa: E402

TID = _boss.TID_RE
# The spec writes the separator as an em dash; `--` is accepted as its ASCII spelling.
DASH = r"(?:—|--)"
HHMM = r"\d{2}:\d{2}"
HEADER_KEYS = {"title", "branch", "pr", "image", "stack", "head", "ci", "milestone"}
TEST_STATES = {"PASS", "FAIL", "BLOCKED", "RUNNING", "PENDING"}
SEVERITIES = {"blocker", "major", "minor"}
TEAM_STATES = {"ACTIVE", "DORMANT", "NEEDS-OWNER"}
MOODS = {"idle", "testing", "bug-found", "fixing", "all-green", "auto"}

RE_TEST = re.compile(rf"^TEST\s+({TID})\s+(PASS|FAIL|BLOCKED|RUNNING|PENDING)(?:\s+{DASH}\s*(.*))?$")
RE_DEFECT_OPEN = re.compile(r'^DEFECT\s+(D\d+)\s+open\s+(blocker|major|minor)\s+"([^"]*)"\s+owner\s+(\S+)$')
RE_DEFECT_MOVE = re.compile(rf"^DEFECT\s+(D\d+)\s+(fixing|fix-pushed\s+(\S+)|verified|deferred|no-bug)(?:\s+{DASH}\s*(.*))?$")
RE_HEADER = re.compile(r"^HEADER\s+(.+)$")
RE_KV = re.compile(r'(\w+)=(?:"([^"]*)"|(\S+))')
RE_TEAM = re.compile(rf"^TEAM\s+(\S+)\s+(ACTIVE|DORMANT|NEEDS-OWNER)\s+{DASH}\s*(.*?)(?:\s+since\s+({HHMM}))?$")
RE_OWNER_NEEDS = re.compile(rf'^OWNER\s+(\S+)\s+NEEDS\s+"([^"]*)"\s+{DASH}\s*(.*)$')
RE_OWNER_CLEAR = re.compile(r"^OWNER\s+(\S+)\s+CLEAR$")
RE_LOG = re.compile(rf"^LOG\s+(?:({HHMM})\s+)?(.+)$")
RE_REMAINING = re.compile(r"^REMAINING\s+(.+)$")
RE_OUTCOME = re.compile(rf"^OUTCOME\s+(GO|NO-GO)\s+{DASH}\s*(.*)$")
RE_MOOD = re.compile(r"^MOOD\s+(idle|testing|bug-found|fixing|all-green|auto)$")
RE_DONE = re.compile(r"^DONE\s+(.+)$")
RE_SUMMARY = re.compile(r"^SUMMARY\s+(did|challenge|followup|clear)(?:\s+(.+))?$")
SUMMARY_KEYS = {"did": "did", "challenge": "challenges", "followup": "followups"}

RE_PHASE = re.compile(r"^###\s+(?:Phase\s+(\d+)|P(\d+))\s+(?:—|--|-)\s+(.+?)\s*$")
RE_PLAN_TEST = re.compile(rf"^-\s+({TID})\s+(\S+):\s+(.+?)\s*$")

UNPLANNED = {"id": "PX", "title": "Unplanned"}


# ---------------------------------------------------------------- state io

def state_path(rdir: str) -> str:
    return os.path.join(rdir, "state.json")


def new_state(run: dict, title: str | None) -> dict:
    return {
        "version": 0,
        "run": {"id": run["id"], "title": title or run.get("title") or run["id"],
                "started": run.get("started"), "tz": run.get("tz")},
        "header": {"branch": run.get("branch"), "pr": None, "image": None, "stack": None, "head": None, "ci": None, "milestone": None},
        "phases": [],
        "defects": [],
        "team": [{"role": r["role"], "session": r.get("session"), "model": r.get("model"),
                  "state": "dormant", "activity": "", "since": None} for r in run.get("roles", [])],
        "owner_calls": [],
        "log": [],
        "remaining": None,
        "outcome": None,
        "done": None,
        "summary": {"did": [], "challenges": [], "followups": []},
        "mood": "idle",
        "mood_override": None,
        "ambiguous": [],
    }


def load_state(rdir: str) -> dict:
    p = state_path(rdir)
    if not os.path.exists(p):
        _boss.die(f"no state.json in {rdir} (run boss-state init first)", 1)
    return _boss.load_json(p)


def save_state(rdir: str, st: dict) -> None:
    st["version"] = int(st.get("version", 0)) + 1
    st["mood"] = derive_mood(st)
    _boss.write_json(state_path(rdir), st)


def derive_mood(st: dict) -> str:
    if st.get("mood_override"):
        return st["mood_override"]
    if st.get("done"):
        return "all-green"
    outcome = st.get("outcome") or {}
    if outcome.get("verdict") == "GO":
        return "all-green"
    if st.get("owner_calls"):
        return "bug-found"
    statuses = {d.get("status") for d in st.get("defects", [])}
    if "open" in statuses:
        return "bug-found"
    if statuses & {"fixing", "fix-pushed"}:
        return "fixing"
    if any(t.get("state") == "running" for ph in st.get("phases", []) for t in ph.get("tests", [])):
        return "testing"
    if any(m.get("state") == "active" for m in st.get("team", [])):
        return "testing"
    return "idle"


# ---------------------------------------------------------------- lookups

def find_test(st: dict, tid: str) -> dict | None:
    for ph in st["phases"]:
        for t in ph["tests"]:
            if t["id"] == tid:
                return t
    return None


def unplanned_phase(st: dict) -> dict:
    for ph in st["phases"]:
        if ph["id"] == UNPLANNED["id"]:
            return ph
    ph = {**UNPLANNED, "tests": []}
    st["phases"].append(ph)
    return ph


def ensure_test(st: dict, tid: str) -> dict:
    t = find_test(st, tid)
    if t is None:
        t = {"id": tid, "title": "(unplanned)", "owner": None, "state": "pending", "evidence": None, "updated": None}
        unplanned_phase(st)["tests"].append(t)
    return t


def find_defect(st: dict, did: str) -> dict | None:
    return next((d for d in st["defects"] if d["id"] == did), None)


def find_member(st: dict, role: str) -> dict | None:
    return next((m for m in st["team"] if m["role"] == role), None)


# ---------------------------------------------------------------- directives

def apply_line(st: dict, line: str, now: str) -> bool:
    """Apply one directive. Returns False when the line does not parse."""
    if (m := RE_TEST.match(line)):
        tid, verdict, evidence = m.groups()
        t = ensure_test(st, tid)
        t["state"] = verdict.lower()
        t["evidence"] = evidence.strip() if evidence else None
        t["updated"] = now
        return True

    if (m := RE_DEFECT_OPEN.match(line)):
        did, sev, title, owner = m.groups()
        d = find_defect(st, did)
        if d is None:
            d = {"id": did, "sev": sev, "title": title, "owner": owner, "status": "open", "commit": None, "notes": []}
            st["defects"].append(d)
        else:
            d.update({"sev": sev, "title": title, "owner": owner, "status": "open"})
        return True

    if (m := RE_DEFECT_MOVE.match(line)):
        did, move, sha, note = m.groups()
        d = find_defect(st, did)
        if d is None:
            # A transition for a defect no one reported: keep it rather than drop it (like unknown tests).
            d = {"id": did, "sev": None, "title": "(unreported)", "owner": None, "status": None, "commit": None, "notes": []}
            st["defects"].append(d)
        if move.startswith("fix-pushed"):
            d["status"] = "fix-pushed"
            d["commit"] = sha
        else:
            d["status"] = move
        if note and note.strip():
            d["notes"].append(note.strip())
        return True

    if (m := RE_HEADER.match(line)):
        rest = m.group(1)
        pairs = RE_KV.findall(rest)
        consumed = "".join(RE_KV.sub("", rest).split())
        if not pairs or consumed:
            return False
        kv = {k: (q if q else u) for k, q, u in pairs}
        if not set(kv) <= HEADER_KEYS:
            return False
        for k, v in kv.items():
            if k == "title":
                st["run"]["title"] = v
            else:
                st["header"][k] = v
        return True

    if (m := RE_TEAM.match(line)):
        role, tstate, activity, since = m.groups()
        mem = find_member(st, role)
        if mem is None:
            mem = {"role": role, "session": f"{st['run']['id']}-{role}", "model": None,
                   "state": "dormant", "activity": "", "since": None}
            st["team"].append(mem)
        mem["state"] = tstate.lower()
        mem["activity"] = activity.strip()
        mem["since"] = since or now
        return True

    if (m := RE_OWNER_NEEDS.match(line)):
        role, command, why = m.groups()
        st["owner_calls"] = [c for c in st["owner_calls"] if c["role"] != role]
        st["owner_calls"].append({"role": role, "command": command, "why": why.strip(), "since": now})
        return True

    if (m := RE_OWNER_CLEAR.match(line)):
        role = m.group(1)
        st["owner_calls"] = [c for c in st["owner_calls"] if c["role"] != role]
        return True

    if (m := RE_LOG.match(line)):
        t, text = m.groups()
        st["log"].insert(0, {"time": t or now, "text": text.strip()})
        return True

    if (m := RE_REMAINING.match(line)):
        text = m.group(1).strip()
        st["remaining"] = None if text == "-" else text
        return True

    if (m := RE_OUTCOME.match(line)):
        verdict, text = m.groups()
        st["outcome"] = {"verdict": verdict, "text": text.strip()}
        return True

    if (m := RE_MOOD.match(line)):
        mood = m.group(1)
        st["mood_override"] = None if mood == "auto" else mood
        return True

    if (m := RE_DONE.match(line)):
        text = m.group(1).strip()
        st["done"] = None if text == "-" else {"headline": text, "at": now}
        return True

    if (m := RE_SUMMARY.match(line)):
        kind, text = m.group(1), (m.group(2) or "").strip()
        summary = st.setdefault("summary", {"did": [], "challenges": [], "followups": []})
        if kind == "clear":
            if text:
                return False
            for k in summary:
                summary[k] = []
            return True
        if not text:
            return False
        summary.setdefault(SUMMARY_KEYS[kind], []).append(text)
        return True

    return False


# ---------------------------------------------------------------- commands

def cmd_init(a) -> int:
    rdir, run = _boss.load_run(a.run)
    st = new_state(run, a.title)
    _boss.write_json(state_path(rdir), st)
    print(f"state v0 written: {state_path(rdir)}")
    return 0


def cmd_plan_import(a) -> int:
    rdir, run = _boss.load_run(a.run)
    st = load_state(rdir)
    try:
        with open(a.plan) as f:
            lines = f.read().splitlines()
    except OSError as e:
        _boss.die(f"cannot read plan: {e}", 1)

    existing = {t["id"]: t for ph in st["phases"] for t in ph["tests"]}
    phases: list[dict] = []
    current: dict | None = None
    seen: set[str] = set()
    for raw in lines:
        line = raw.rstrip()
        if (m := RE_PHASE.match(line)):
            n = m.group(1) or m.group(2)
            current = {"id": f"P{n}", "title": m.group(3), "tests": []}
            phases.append(current)
            continue
        if (m := RE_PLAN_TEST.match(line)):
            tid, owner, title = m.groups()
            if tid in seen:
                continue
            seen.add(tid)
            if current is None:
                current = {**UNPLANNED, "tests": []}
                phases.append(current)
            old = existing.get(tid)
            t = {"id": tid, "title": title, "owner": owner,
                 "state": old["state"] if old else "pending",
                 "evidence": old["evidence"] if old else None,
                 "updated": old["updated"] if old else None}
            current["tests"].append(t)

    # Tests the state knows that the plan no longer lists stay visible under Unplanned.
    leftovers = [t for tid, t in existing.items() if tid not in seen]
    if leftovers:
        ph = next((p for p in phases if p["id"] == UNPLANNED["id"]), None)
        if ph is None:
            ph = {**UNPLANNED, "tests": []}
            phases.append(ph)
        ph["tests"].extend(leftovers)

    st["phases"] = phases
    save_state(rdir, st)

    dest = os.path.join(rdir, "plan.md")
    if os.path.realpath(a.plan) != os.path.realpath(dest):
        shutil.copyfile(a.plan, dest)
    ntests = sum(len(p["tests"]) for p in phases)
    print(f"imported {len(phases)} phases, {ntests} tests -> state v{st['version']}")
    return 0


def cmd_apply(a) -> int:
    rdir, run = _boss.load_run(a.run)
    st = load_state(rdir)
    if a.file:
        try:
            with open(a.file) as f:
                text = f.read()
        except OSError as e:
            _boss.die(f"cannot read feed: {e}", 1)
    else:
        text = sys.stdin.read()

    now = _boss.hhmm(st["run"].get("tz") or run.get("tz") or "UTC")
    applied = 0
    ambiguous: list[str] = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if apply_line(st, line, now):
            applied += 1
        else:
            ambiguous.append(line)
    st["ambiguous"] = ambiguous
    save_state(rdir, st)
    print(f"applied: {applied}")
    for line in ambiguous:
        print(f"ambiguous: {line}")
    return 0


def cmd_show(a) -> int:
    rdir, _ = _boss.load_run(a.run)
    st = load_state(rdir)
    tests = [t for ph in st["phases"] for t in ph["tests"]]
    counts = {k: sum(1 for t in tests if t["state"] == k) for k in ("pass", "fail", "blocked", "running", "pending")}
    print(f"{st['run']['id']} — {st['run']['title']}   version {st['version']}   mood {st['mood']}"
          + (f" (override)" if st.get("mood_override") else ""))
    hdr = {k: v for k, v in st["header"].items() if v}
    if hdr:
        print("header: " + " ".join(f"{k}={v}" for k, v in hdr.items()))
    print(f"tests: {len(tests)}  pass {counts['pass']}  fail {counts['fail']}  blocked {counts['blocked']}"
          f"  running {counts['running']}  pending {counts['pending']}")
    open_defects = [d for d in st["defects"] if d["status"] not in ("verified", "no-bug")]
    print(f"defects: {len(st['defects'])} total, {len(open_defects)} unresolved")
    for d in open_defects:
        commit = f" {d['commit']}" if d.get("commit") else ""
        print(f"  {d['id']} {d['sev'] or '?'} {d['status']}{commit} — {d['title']} (owner {d['owner']})")
    if st["owner_calls"]:
        print("owner calls:")
        for c in st["owner_calls"]:
            print(f"  {c['role']} NEEDS \"{c['command']}\" — {c['why']} (since {c['since']})")
    active = [m for m in st["team"] if m["state"] != "dormant"]
    if active:
        print("team: " + "; ".join(f"{m['role']} {m['state']} — {m['activity']}" for m in active))
    if st.get("remaining"):
        print(f"remaining: {st['remaining']}")
    if st.get("outcome"):
        print(f"outcome: {st['outcome']['verdict']} — {st['outcome']['text']}")
    if st["log"]:
        print(f"last log: {st['log'][0]['time']} {st['log'][0]['text']}")
    if st["ambiguous"]:
        print(f"ambiguous (last apply): {len(st['ambiguous'])}")
    return 0


def main(argv) -> int:
    p = argparse.ArgumentParser(prog="boss-state", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("init"); s.add_argument("--title"); s.add_argument("--run"); s.set_defaults(fn=cmd_init)
    s = sub.add_parser("plan-import"); s.add_argument("plan"); s.add_argument("--run"); s.set_defaults(fn=cmd_plan_import)
    s = sub.add_parser("apply"); s.add_argument("file", nargs="?"); s.add_argument("--run"); s.set_defaults(fn=cmd_apply)
    s = sub.add_parser("show"); s.add_argument("--run"); s.set_defaults(fn=cmd_show)

    a = p.parse_args(argv)
    return a.fn(a)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
