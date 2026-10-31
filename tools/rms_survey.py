#!/usr/bin/env python3
"""
Show which commands of a folder of random map scripts the converter does not read yet (#4037).

Usage:
    python3 tools/rms_survey.py DIR > survey.md

For each `*.rms` file of DIR, the land of the script is made with seed 1 (`rmap.generate`). The output is Markdown:
a table of the maps with their warnings, a table of the warnings with the number of maps that have each one, and a
table of the labels that the scripts test and no script defines (the `if` labels, with the number of maps).
The output holds no script text: paste it on a public ticket.
"""
import argparse
import glob
import os
import sys
import traceback
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
        rmap.generate(text, 1, warn=warnings.append, folder=os.path.dirname(path), name=os.path.basename(path))
        state = "ok"
    except Exception as e:  # one broken script must not stop the survey
        state = f"error: {type(e).__name__}: {e}"
        if not isinstance(e, rmap.RmsError) and e.__traceback__:  # the place of a bug, no script text
            f = traceback.extract_tb(e.__traceback__)[-1]
            state += f" (at {os.path.basename(f.filename)}:{f.lineno} {f.name})"
    return list(dict.fromkeys(warnings)), state


def labels(text, folder, depth=0):
    """The labels that a script tests (after if or elseif) and the labels it defines (#define), with those of its
    #include_drs files (the same folder, as in rmap.expand). Only the names: no script text is kept."""
    words = rmap.tokens(text)
    tested, defined = set(), set()
    for i, w in enumerate(words[:-1]):
        if w in ("if", "elseif"):
            tested.add(words[i + 1])
        elif w == "#define":
            defined.add(words[i + 1])
        elif w == "#include_drs" and depth < 8:
            path = os.path.join(folder, *words[i + 1].replace("\\", "/").split("/"))
            if os.path.isfile(path):
                with open(path, encoding="utf-8", errors="replace") as f:
                    t, d = labels(f.read(), folder, depth + 1)
                tested |= t
                defined |= d
    return tested, defined


def undefined(folder):
    """The labels that the scripts of folder test and that no script defines, with the number of maps that test each."""
    maps = Counter()
    for path in sorted(glob.glob(os.path.join(folder, "*.rms"))):
        with open(path, encoding="utf-8", errors="replace") as f:
            tested, defined = labels(f.read(), folder)
        maps.update(tested - defined - {label for _, label in rmap.LABELS})
    return maps


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
    print("\n| Label | Maps |\n| --- | --- |")
    for label, count in sorted(undefined(a.dir).items(), key=lambda kv: (-kv[1], kv[0])):
        print(f"| {label} | {count} |")


if __name__ == "__main__":
    main()
