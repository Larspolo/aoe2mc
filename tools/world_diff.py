#!/usr/bin/env python3
"""
Compare two converted worlds without their time stamps (#702).

Usage:
    python3 tools/world_diff.py WORLD_A WORLD_B

A conversion writes the time into each world: the time table of each .mca file (bytes 4096-8191), the gzip header
of each .dat file and "LastPlayed" in level.dat. This tool skips them. Exit 0 and "same" when all other bytes are
the same, else exit 1 and the names of the files that differ.
"""
import gzip
import os
import sys


def files(root):
    return sorted(os.path.relpath(os.path.join(r, f), root) for r, _, fs in os.walk(root) for f in fs)


def content(path, name):
    data = open(path, "rb").read()
    if name.endswith(".mca"):
        return data[:4096] + data[8192:]
    if data[:2] == b"\x1f\x8b":
        data = gzip.decompress(data)
        i = data.find(b"LastPlayed") if os.path.basename(name) == "level.dat" else -1
        if i >= 0:
            data = data[:i] + data[i + len("LastPlayed") + 8:]          # the name, then a long of 8 bytes
    return data


def diff(a, b):
    """Names of the files that differ or are in one world only."""
    fa, fb = files(a), files(b)
    return sorted(set(fa) ^ set(fb)) + [f for f in fa if f in set(fb)
                                        and content(os.path.join(a, f), f) != content(os.path.join(b, f), f)]


def main(argv=None):
    a, b = (argv or sys.argv[1:])[:2]
    bad = diff(a, b)
    print("same" if not bad else "differ: " + ", ".join(bad))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
