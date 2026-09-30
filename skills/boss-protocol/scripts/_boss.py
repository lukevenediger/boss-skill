"""Shared helpers for the boss-protocol scripts. Standard library only."""
import json
import os
import subprocess
import sys
from datetime import datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

TID_RE = r"[A-Z]\d+\.\d+"


def boss_home() -> str:
    return os.environ.get("BOSS_HOME") or os.path.join(os.path.expanduser("~"), ".boss")


def die(msg: str, code: int = 2) -> "NoReturn":
    sys.stderr.write(msg.rstrip("\n") + "\n")
    sys.exit(code)


def current_run_id() -> str:
    p = os.path.join(boss_home(), "current")
    try:
        with open(p) as f:
            rid = f.read().strip()
    except FileNotFoundError:
        die(f"no active run: {p} missing (run boss-run init)")
    if not rid:
        die(f"no active run: {p} is empty")
    return rid


def run_dir(run_id: str | None = None) -> str:
    return os.path.join(boss_home(), "runs", run_id or current_run_id())


def load_json(path: str):
    try:
        with open(path) as f:
            return json.load(f)
    except FileNotFoundError:
        die(f"missing {path}")
    except json.JSONDecodeError as e:
        die(f"corrupt JSON in {path}: {e}")


def write_json(path: str, data) -> None:
    """Atomic replace so a reader never sees a half-written file."""
    tmp = f"{path}.tmp.{os.getpid()}"
    with open(tmp, "w") as f:
        json.dump(data, f, indent=1, ensure_ascii=False)
        f.write("\n")
    os.replace(tmp, path)


def load_run(run_id: str | None = None) -> tuple[str, dict]:
    d = run_dir(run_id)
    return d, load_json(os.path.join(d, "run.json"))


def system_tz_name() -> str:
    """Best-effort IANA name of the machine's zone; falls back to `date +%Z`."""
    for candidate in (os.environ.get("TZ"),):
        if candidate:
            try:
                ZoneInfo(candidate)
                return candidate
            except (ZoneInfoNotFoundError, ValueError):
                pass
    try:
        target = os.path.realpath("/etc/localtime")
        marker = "zoneinfo/"
        if marker in target:
            name = target.rsplit(marker, 1)[1]
            ZoneInfo(name)
            return name
    except (OSError, ZoneInfoNotFoundError, ValueError):
        pass
    try:
        out = subprocess.run(["date", "+%Z"], capture_output=True, text=True, check=True).stdout.strip()
        if out:
            return out
    except (OSError, subprocess.CalledProcessError):
        pass
    return "UTC"


def zone(tz_name: str):
    try:
        return ZoneInfo(tz_name)
    except (ZoneInfoNotFoundError, ValueError):
        # A non-IANA name (e.g. an abbreviation from `date +%Z`) still needs a clock.
        return datetime.now().astimezone().tzinfo


def now_in(tz_name: str) -> datetime:
    """Now in the run's tz. BOSS_NOW=YYYY-MM-DDTHH:MM[:SS] (naive, run-local) pins it for tests."""
    override = os.environ.get("BOSS_NOW")
    z = zone(tz_name)
    if override:
        try:
            naive = datetime.fromisoformat(override)
        except ValueError:
            die(f"BOSS_NOW is not ISO-8601: {override!r}")
        if naive.tzinfo is None:
            return naive.replace(tzinfo=z)
        return naive.astimezone(z)
    return datetime.now(z)


def iso_ts(tz_name: str) -> str:
    return now_in(tz_name).isoformat(timespec="seconds")


def hhmm(tz_name: str) -> str:
    return now_in(tz_name).strftime("%H:%M")


def today(tz_name: str) -> str:
    return now_in(tz_name).strftime("%Y-%m-%d")


def compact_json(data) -> str:
    return json.dumps(data, separators=(",", ":"), ensure_ascii=False)
