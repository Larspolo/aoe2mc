#!/usr/bin/env python3
"""Find the tests that check the content of the unit data (#5388): they fail when a value of a data file changes.

Usage: python3 tools/data_shake.py TEST_FILE... [--seed N] [--drop P] [--keep DIR]

The tool writes a data mod folder (#5353, `game/table.py` `MOD`) with changed lines of `game/data/units.jsonl` and
`game/data/buildings.jsonl`: each number of the stats changes by a seeded factor (a zero stays zero, the sign stays),
and each bonus changes or, with the chance P, goes away. The form of each line stays valid. Then it runs the test
files without and with `AOE2MC_DATA_MOD` and prints each test that fails only with the changed data. Such a test
breaks the owner rule "no test checks the content of a data file" (CLAUDE.md, #4177): rewrite it with test data or
with the expected value from the data, or remove it when another test checks the logic (#5311).
Exit 0: no such test, 1: tests found.
"""
import argparse
import json
import os
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "game", "data")
FILES = ("units.jsonl", "buildings.jsonl")
KEYS = ("hp", "attack", "melee", "pierce", "range", "reload")   # the numbers of combat.Stats


def change(v, rng):
    """`v` changed by a factor of 1.2 to 1.6, the same type and sign; 0 stays 0 (a melee unit stays melee)."""
    if not v or isinstance(v, bool):
        return v
    if isinstance(v, float):
        return round(v * rng.uniform(1.2, 1.6), 2)
    w = int(round(v * rng.uniform(1.2, 1.6)))
    return w if w != v else v + (1 if v > 0 else -1)


def shake(rows, rng, drop=0.5):
    """The mod lines of `rows`: the name and the changed numbers and bonus of each row."""
    out = []
    for r in rows:
        line = {"name": r["name"]} | {k: change(r[k], rng) for k in KEYS if k in r}
        if "bonus" in r:
            keep = [c for c in sorted(r["bonus"]) if rng.random() >= drop]
            line["bonus"] = {c: change(r["bonus"][c], rng) for c in keep}
        out.append(line)
    return out


def write_mod(folder, seed=0, drop=0.5):
    """Write the changed lines of FILES into `folder`."""
    rng = np.random.default_rng(seed)
    for f in FILES:
        rows = [json.loads(s) for s in open(os.path.join(DATA, f), encoding="utf-8") if s.strip()]
        with open(os.path.join(folder, f), "w", encoding="utf-8") as out:
            out.writelines(json.dumps(r) + "\n" for r in shake(rows, rng, drop))


def failed(tests, mod=None, args=()):
    """The node IDs of the tests of `tests` that fail or stop, with the data mod folder `mod`."""
    env = dict(os.environ, PYTHONPATH=os.pathsep.join(filter(None, (ROOT, os.environ.get("PYTHONPATH")))))
    env.pop("AOE2MC_DATA_MOD", None)
    if mod:
        env["AOE2MC_DATA_MOD"] = mod
    with tempfile.TemporaryDirectory() as tmp:
        xml = os.path.join(tmp, "out.xml")
        subprocess.run([sys.executable, "-m", "pytest", "-p", "no:cacheprovider", "-q", f"--junitxml={xml}", *args,
                        *tests], cwd=ROOT, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if not os.path.exists(xml):
            return set()
        cases = ET.parse(xml).getroot().iter("testcase")
        return {f"{c.get('classname')}::{c.get('name')}" for c in cases if c.find("failure") is not None
                or c.find("error") is not None}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("tests", nargs="+", help="test files or node IDs")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--drop", type=float, default=0.5, help="the chance that a bonus goes away (default 0.5)")
    ap.add_argument("--keep", metavar="DIR", help="write the data mod folder to DIR and keep it")
    ap.add_argument("-n", default=None, help="pytest-xdist workers (for example auto)")
    a = ap.parse_args(argv)
    args = ("-n", a.n) if a.n else ()
    with tempfile.TemporaryDirectory() as tmp:
        mod = a.keep or tmp
        os.makedirs(mod, exist_ok=True)
        write_mod(mod, a.seed, a.drop)
        bad = sorted(failed(a.tests, mod, args) - failed(a.tests, None, args))
    for t in bad:
        print(t)
    print(f"{len(bad)} test(s) check the content of the unit data (seed {a.seed})", file=sys.stderr)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
