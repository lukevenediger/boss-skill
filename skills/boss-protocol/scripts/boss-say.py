#!/usr/bin/env python3
"""boss-say: assign the next M<n>, append the record, print the message to pass to SendMessage (§3).

  boss-say --from <role> --to <role> --re <ref> [--reply M<k>] --subject "<one line>"
           [--body <text> | --body-file <path> | body on stdin] [--run <id>]

Exit 2 on validation errors, with a one-line reason on stderr.
"""
import argparse
import fcntl
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.realpath(__file__)))
import _boss  # noqa: E402

# §3: RUN · P<n>.<m> · T<n>.<m> · D<n> · M<n> · OWNER. The test-id form is widened to §4's
# `[A-Z]\d+\.\d+` so a message can reference V1.2 the way a feed line can.
RE_REF = re.compile(r"^(RUN|OWNER|[A-Z]\d+\.\d+|D\d+|M\d+)$")
RE_MSG = re.compile(r"^M\d+$")
SUBJECT_MAX = 200


def read_body(a) -> str:
    if a.body is not None and a.body_file:
        _boss.die("use --body or --body-file, not both")
    if a.body is not None:
        return a.body
    if a.body_file:
        try:
            with open(a.body_file) as f:
                return f.read()
        except OSError as e:
            _boss.die(f"cannot read --body-file {a.body_file!r}: {e} (use --body \"<text>\" for inline text)")
    if not sys.stdin.isatty():
        return sys.stdin.read()
    return ""


def main(argv) -> int:
    p = argparse.ArgumentParser(prog="boss-say", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--from", dest="from_", required=True, metavar="ROLE")
    p.add_argument("--to", required=True, metavar="ROLE")
    p.add_argument("--re", required=True, metavar="REF")
    p.add_argument("--reply", metavar="M<k>")
    p.add_argument("--subject", required=True)
    p.add_argument("--body", help="inline body text (markdown)")
    p.add_argument("--body-file")
    p.add_argument("--run")
    try:
        a = p.parse_args(argv)
    except SystemExit:
        return 2

    rdir, run = _boss.load_run(a.run)
    roles = {r["role"] for r in run.get("roles", [])} | {"owner"}
    if a.from_ not in roles:
        _boss.die(f"unknown --from role {a.from_!r}; valid: {', '.join(sorted(roles))}")
    if a.to not in roles:
        _boss.die(f"unknown --to role {a.to!r}; valid: {', '.join(sorted(roles))}")
    if not RE_REF.match(a.re):
        _boss.die(f"bad --re {a.re!r}; expected RUN, P<n>.<m>, T<n>.<m>, D<n>, M<n> or OWNER")
    if a.reply is not None and not RE_MSG.match(a.reply):
        _boss.die(f"bad --reply {a.reply!r}; expected M<k>")
    subject = a.subject.strip()
    if not subject:
        _boss.die("subject is empty")
    if "\n" in subject or "\r" in subject:
        _boss.die("subject must be a single line")
    if len(subject) > SUBJECT_MAX:
        _boss.die(f"subject is {len(subject)} chars; max {SUBJECT_MAX}")

    body = read_body(a).rstrip("\n")
    conv = os.path.join(rdir, "conversation.jsonl")

    # Exclusive lock on the conversation file itself: read max id, append, release.
    with open(conv, "a+", encoding="utf-8") as f:
        fcntl.flock(f.fileno(), fcntl.LOCK_EX)
        try:
            f.seek(0)
            max_id = 0
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rid = json.loads(line).get("id", "")
                except json.JSONDecodeError:
                    continue
                if RE_MSG.match(rid):
                    max_id = max(max_id, int(rid[1:]))
            mid = f"M{max_id + 1}"
            record = {
                "id": mid,
                "ts": _boss.iso_ts(run["tz"]),
                "from": a.from_,
                "to": a.to,
                "re": a.re,
                "reply_to": a.reply,
                "subject": subject,
                "body": body,
            }
            f.seek(0, os.SEEK_END)
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
            f.flush()
            os.fsync(f.fileno())
        finally:
            fcntl.flock(f.fileno(), fcntl.LOCK_UN)

    header = f"[{mid} {a.from_}→{a.to} re:{a.re}"
    if a.reply:
        header += f" reply:{a.reply}"
    header += f"] {subject}"
    out = header if not body else f"{header}\n\n{body}"
    sys.stdout.write(out + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
