#!/usr/bin/env python3
"""
Run each example of the AoE2 AI Scripting Encyclopedia on a bot and print the crashes and the "unknown" warnings
(#5192): the checks of #4526 by hand, in one command.

Usage:
    python3 tools/airef_probe.py [FILE]        # FILE: a local commands.js; none: the file is downloaded to out/airef/

Each example is a script in `data` (a JS string). It runs 3 steps of the script on the bot of test_bot_gather.bot_map().
Exit 1 when an example crashes, and the crash is not a missing (load) file.
"""
import argparse
import contextlib
import html
import io
import json
import os
import re
import sys
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path[:0] = [ROOT, HERE, os.path.join(ROOT, "tests"), os.path.join(ROOT, "game")]

import per  # noqa: E402
from test_bot_gather import bot_map  # noqa: E402

URL = "https://airef.github.io/js/commands.js"
CACHE = os.path.join(ROOT, "out", "airef", "commands.js")
COMMAND = re.compile(r"(\w+)\.example\s*=")                       # cX.example = [ ... ]
EXAMPLE = re.compile(r'\{\s*title:\s*"((?:[^"\\]|\\.)*)"\s*,\s*data:\s*"((?:[^"\\]|\\.)*)"')


def js_string(s):
    """The text of a JS string literal (its body): the JSON escapes, then the HTML entities."""
    return html.unescape(json.loads('"' + s + '"', strict=False))


def examples(text):
    """(command, title, script) of each example of the file."""
    found = list(COMMAND.finditer(text))
    out = []
    for i, m in enumerate(found):
        end = found[i + 1].start() if i + 1 < len(found) else len(text)
        for t, d in EXAMPLE.findall(text[m.end():end]):
            out.append((m[1], js_string(t), js_string(d)))
    return out


def run(script):
    """(the warning lines, the exception or None) of 3 steps of the script on a bot."""
    err = io.StringIO()
    try:
        with contextlib.redirect_stderr(err):
            server, me, b = bot_map()
            b.script = per.Script(per.parse(script), b)
            for _ in range(3):
                b.script.step()
    except Exception as e:                                           # a crash of the script: reported, not raised
        return err.getvalue(), e
    return err.getvalue(), None


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    ap.add_argument("file", nargs="?", help="a local commands.js (default: downloaded once to out/airef/)")
    args = ap.parse_args(argv)
    if args.file:
        path = args.file
    else:
        path = CACHE
        if not os.path.exists(path):
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with urllib.request.urlopen(URL, timeout=120) as r, open(path, "wb") as f:
                f.write(r.read())
    with open(path, encoding="utf-8", errors="replace") as f:
        found = examples(f.read())
    crashes, warnings = [], {}
    for command, title, script in found:
        text, e = run(script)
        if e is not None and "for load" not in str(e):                 # a (load "FILE") with no file: not a crash
            crashes.append((command, title, type(e).__name__, str(e), script))
        for line in text.splitlines():
            if line.startswith("AI script"):
                commands = warnings.setdefault(line, [])
                if command not in commands:
                    commands.append(command)
    print(f"examples: {len(found)}")
    print(f"crashes: {len(crashes)}")
    for command, title, kind, message, script in crashes:
        print(f"  {command} ({title}): {kind}: {message}")
        print(f"    {script[:200]!r}")
    print(f"warnings: {len(warnings)} kinds")
    for line, commands in sorted(warnings.items(), key=lambda kv: -len(kv[1])):
        print(f"  {len(commands)} x {line}  [{', '.join(commands[:3])}]")
    return 1 if crashes else 0


if __name__ == "__main__":
    sys.exit(main())
