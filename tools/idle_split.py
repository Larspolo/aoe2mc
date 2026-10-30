#!/usr/bin/env python3
"""
Split the idle villager time of an offline replay (no server) by the cause (#4063).

Usage:
    python3 aoe2mc.py samples/de-64.3.aoe2record OUTWorld
    python3 tools/idle_split.py OUTWorld/aoe2mc.json [--top 30] [--unit 10084,9997 --from 25:00 --to 30:00]

It runs `Replay(Fake(), data, ai=True).run(speed=10000)` (about 2 minutes for de-64.3) and prints the idle time of
each player (as the summary) and the minutes per cause: the player, the kind and target of the last record event of
the villager before it went idle, and its task at that event. Then the longest idle spans (seconds, start, unit
IDs, last event). `--unit` prints each change of the task, job, work tile and cell of these units in the time span.
"""
import argparse
import collections
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path[:0] = [os.path.join(ROOT, "game"), ROOT]


def clock(ms):
    return "%d:%02d" % divmod(ms // 1000, 60)


def seconds(text):
    m, s = text.split(":")
    return (int(m) * 60 + int(s)) * 1000


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("data", help="aoe2mc.json of a converted record")
    ap.add_argument("--top", type=int, default=30)
    ap.add_argument("--unit", default="", help="record IDs to trace, comma separated")
    ap.add_argument("--from", dest="t0", default="0:00")
    ap.add_argument("--to", dest="t1", default="999:00")
    a = ap.parse_args()
    import contextlib
    import json
    import replay

    class Fake:
        def command(self, cmd):
            return ""

    last, cause, rows, spans, seen = {}, {}, collections.Counter(), [], {}
    watch, t0, t1 = [int(i) for i in a.unit.split(",") if i], seconds(a.t0), seconds(a.t1)
    commands, idle_time = replay.Replay.commands, replay.Replay.idle_time

    def on_command(self, e):
        for i in e.get("objects") or ():
            v, t = self.units.get(i), e.get("target")
            what = e.get("name") or (getattr(self.units.get(t), "name", None) if t is not None else None) or t
            last[i] = (e["time"], e["kind"], what, getattr(v, "task", None))
        return commands(self, e)

    def on_idle(self, t):
        before = dict(self.waiting)
        idle_time(self, t)
        ids = {}
        for i, v in self.units.items():
            ids.setdefault(v.uuid, []).append(i)
        for u, (p, _) in self.waiting.items():                     # the cause: the last event when it went idle
            cause.setdefault(u, (max((last[i] for i in ids.get(u, ()) if i in last), default=None), ids.get(u), t))
        for u, (p, s) in before.items():
            if u not in self.waiting:                               # a later command: the summary counts it
                ev, refs, start = cause.pop(u, (None, None, t))
                rows[(p, *(ev[1:] if ev else ("spawn", None, None)))] += s
                spans.append((s, p, start, refs, ev))
        for i in watch:
            if t0 <= t <= t1 and (v := self.units.get(i)) is not None:
                state = (v.task, v.job, v.tree, tuple(round(c) for c in v.cell), i in self.entering)
                if seen.get(i) != state:
                    seen[i] = state
                    print(clock(t), i, state)

    replay.Replay.commands, replay.Replay.idle_time = on_command, on_idle
    r = replay.Replay(Fake(), json.load(open(a.data)), ai=True)
    with contextlib.redirect_stdout(sys.stderr) if not watch else contextlib.nullcontext():
        r.run(speed=10000, log=None)
    for p in sorted(r.idled):
        print("P%s idle %s" % (p, clock(round(r.idled[p] * 1000))))
    print("minutes by (player, last event, its target, task at the event):")
    for k, s in rows.most_common(a.top):
        print(f"  {s / 60:6.1f} {k}")
    print("longest spans (s, player, start, IDs, last event):")
    for s, p, start, refs, ev in sorted(spans, key=lambda r: -r[0])[:a.top]:
        print(f"  {s:5.0f} P{p} {clock(start)} {refs} {ev and (clock(ev[0]), *ev[1:])}")


if __name__ == "__main__":
    main()
