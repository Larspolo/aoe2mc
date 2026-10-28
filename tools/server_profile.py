#!/usr/bin/env python3
"""
Profile the server thread of a running Paper server with Java Flight Recorder (#3336).

Usage:
    python3 tools/server_profile.py [--seconds 60] [--pid PID] [--top 25] [--keep F.jfr]
    python3 tools/server_profile.py --read F.jfr               # only print the tables of a recording

The tool finds the server (`pgrep -f "[j]ava -Xmx2G"`, the `game/run.py` and `mc_check` servers), records with
`jcmd PID JFR.start settings=profile`, dumps the file and reads `jfr print --events jdk.ExecutionSample` as text,
line by line (`--json` of 3 minutes is 1.5 GB, #2761). It prints the top methods of the "Server thread" by own
samples (the top frame) and by inclusive samples (the method is in the stack). #2761 found a slow tick this way:
65 % in the villager brain, `YieldJobSite.canReachPos`.
"""
import argparse
import collections
import os
import re
import subprocess
import sys
import tempfile
import time

THREAD = "Server thread"
FRAME = re.compile(r"^\s+([\w$.<>/]+)\(.*\)\s+line:")


def samples(lines, thread=THREAD):
    """Yield the stack (top frame first) of each jdk.ExecutionSample of thread in `jfr print` text lines."""
    stack, inside, mine = [], False, False
    for line in lines:
        s = line.strip()
        if s.startswith("jdk.ExecutionSample"):
            stack, inside, mine = [], False, False
        elif s.startswith("sampledThread"):
            mine = f'"{thread}"' in s
        elif s.startswith("stackTrace = ["):
            inside = True
        elif inside and s.startswith("]"):
            inside = False
            if mine and stack:
                yield stack
        elif inside and (m := FRAME.match(line)):
            stack.append(m.group(1))


def count(stacks):
    """(own, inclusive, total): Counters of methods, and the number of samples."""
    own, incl, n = collections.Counter(), collections.Counter(), 0
    for st in stacks:
        n += 1
        own[st[0]] += 1
        incl.update(set(st))
    return own, incl, n


def table(own, incl, n, top=25):
    out = [f"{n} samples of the {THREAD}"]
    for title, c in (("own", own), ("inclusive", incl)):
        out += ["", f"{'%':>6}  {'samples':>7}  method ({title})"]
        out += [f"{100 * k / max(n, 1):6.1f}  {k:7d}  {m}" for m, k in c.most_common(top)]
    return "\n".join(out)


def server_pid():
    pids = subprocess.run(["pgrep", "-f", "[j]ava -Xmx2G"], capture_output=True, text=True).stdout.split()
    if not pids:
        raise SystemExit("no Paper server runs (pgrep -f \"[j]ava -Xmx2G\"): start game/run.py first")
    return int(pids[0])


def start(pid, name="aoe2mc"):
    subprocess.run(["jcmd", str(pid), "JFR.start", f"name={name}", "settings=profile"], check=True,
                   capture_output=True)


def stop(pid, path, name="aoe2mc"):
    subprocess.run(["jcmd", str(pid), "JFR.dump", f"name={name}", f"filename={os.path.abspath(path)}"], check=True,
                   capture_output=True)
    subprocess.run(["jcmd", str(pid), "JFR.stop", f"name={name}"], capture_output=True)


def report(path, top=25):
    """The tables of a .jfr file."""
    p = subprocess.Popen(["jfr", "print", "--events", "jdk.ExecutionSample", "--stack-depth", "80", path],
                         stdout=subprocess.PIPE, text=True)
    try:
        res = table(*count(samples(p.stdout)), top)
    finally:
        p.stdout.close()
        p.wait()
    return res


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0].strip(),
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--seconds", type=float, default=60, help="seconds to record (default 60)")
    ap.add_argument("--pid", type=int, help="the Java process (default: the Paper server)")
    ap.add_argument("--top", type=int, default=25, help="rows of each table (default 25)")
    ap.add_argument("--keep", metavar="F.jfr", help="keep the recording in this file")
    ap.add_argument("--read", metavar="F.jfr", help="only print the tables of a recording")
    a = ap.parse_args(argv)
    if a.read:
        print(report(a.read, a.top))
        return
    pid = a.pid or server_pid()
    with tempfile.TemporaryDirectory() as tmp:
        path = a.keep or os.path.join(tmp, "server.jfr")
        start(pid)
        print(f"recording {a.seconds:g} s of process {pid}", file=sys.stderr)
        time.sleep(a.seconds)
        stop(pid, path)
        print(report(path, a.top))


if __name__ == "__main__":
    main()
