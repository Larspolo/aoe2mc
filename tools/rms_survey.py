#!/usr/bin/env python3
"""
Show which commands of a folder of random map scripts the converter does not read yet (#4037).

Usage:
    python3 tools/rms_survey.py DIR > survey.md

For each `*.rms` file of DIR, the land of the script is made with seed 1 (`rmap.generate`). The output is Markdown:
a table of the maps with their warnings, and a table of the warnings with the number of maps that have each one.
The output holds no script text: paste it on a public ticket.
"""
import argparse
import glob
import os
import sys
from collections import Counter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import rmap  # noqa: E402

SHOWN = 5  # the warnings of a map row before "+N"


def survey(path):
    """The distinct warnings of one script and its state ("ok" or "error: ...")."""
    with open(path, encoding="utf-8", errors="replace") as f:
        text = f.read()
    warnings = []
    try:
        rmap.generate(text, 1, warn=warnings.append, folder=os.path.dirname(path))
        state = "ok"
    except Exception as e:  # one broken script must not stop the survey
        state = f"error: {type(e).__name__}: {e}"
    return list(dict.fromkeys(warnings)), state


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("dir")
    a = ap.parse_args()
    rows = []
    maps = Counter()
    for path in sorted(glob.glob(os.path.join(a.dir, "*.rms"))):
        warnings, state = survey(path)
        rows.append((os.path.basename(path)[:-4], warnings, state))
        maps.update(warnings)
    print("| Map | Warnings | State |\n| --- | --- | --- |")
    for name, warnings, state in rows:
        shown = "; ".join(warnings[:SHOWN]) + (f"; +{len(warnings) - SHOWN}" if len(warnings) > SHOWN else "")
        print(f"| {name} | {len(warnings)} | {shown or 'ok'} |" if state == "ok" else f"| {name} | 0 | {state} |")
    print("\n| Warning | Maps |\n| --- | --- |")
    for text, count in sorted(maps.items(), key=lambda kv: (-kv[1], kv[0])):
        print(f"| {text} | {count} |")


if __name__ == "__main__":
    main()
