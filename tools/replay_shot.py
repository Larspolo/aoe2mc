#!/usr/bin/env python3
"""
Real client screenshots at given game times of a live replay (#5273): a check sees the trigger titles and the units
that the replay makes (#5235).

Usage:
    python3 tools/replay_shot.py samples/de-trigger-test.aoe2record OUT.png --at-time 0:11 --at-time 0:31 \
        [--view X,Y,Z,YAW,PITCH] [--speed 1]

SRC is a record (the tool converts it) or a converted world of a record. The replay runs on Paper as
`run.py --replay` (replay.Replay with the boss bar); the client of mc_shot.Client joins as a spectator. At each
--at-time the poll of the replay saves the X screen: OUT_0m11s.png, OUT_0m31s.png ... One --view: the camera of all
shots; else the camera stands 2 blocks above the spawn. Minecraft feature: the client and the Paper server of
run.Game, nothing new in Minecraft.

The info line check (#5461, level 4 of the verify skill: a change of the replay info line or the camera runs it before
the push, the method of the checks #5439 and #5442):
    python3 tools/replay_shot.py samples/de-64.3.aoe2record out/c.png --at-time 1:00 --camera player --info out/c.json

--camera: the camera mode of the replay (run.py --camera); the client is a spectator from the start, and with
`player` the shots keep the view of the camera entity. --info: log the action bar lines of Replay.inspect and write
their count of units and buildings and the first line of each to the JSON file. Exit 1: no unit line.
"""
import argparse
import contextlib
import io
import json
import os
import shutil
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path[:0] = [ROOT, HERE, os.path.join(ROOT, "game")]

import mc_shot  # noqa: E402

import aoe2mc  # noqa: E402


class Done(Exception):
    """The poll took the last shot: stop the replay."""


def plan(out, times):
    """The shots of the --at-time values times (MM:SS): sorted (game time in ms, PNG path), one per time."""
    base = out[:-4] if out.lower().endswith(".png") else out
    ms = sorted({aoe2mc.game_time(t) for t in times})
    return [(t, f"{base}_{t // 60000}m{t // 1000 % 60:02d}s.png") for t in ms]


def due(shots, now):
    """The shots of plan() with a game time at or before now (ms): the poll takes them now."""
    return [s for s in shots if s[0] <= now]


def summary(lines):
    """The --info JSON of the logged (game time in ms, command) lines of Replay.inspect (#5461): the count of unit and
    of building lines and the first line of each kind. A unit line has the key aoe2mc.replay.inspect."""
    out = {"unit": 0, "building": 0, "first": {}}
    for t, cmd in lines:
        t, kind = int(t), "unit" if "aoe2mc.replay.inspect" in cmd else "building"   # the replay time is a float
        out[kind] += 1
        out["first"].setdefault(kind, [f"{t // 60000}:{t // 1000 % 60:02d}", cmd])
    return out


def run_shots(src, out, times, view=None, speed=1.0, version=None, settle=3.0, camera=None, info=None):
    """Play the replay of src and save a client screenshot at each game time of times; returns the PNG paths. info: a
    list that gets the (game time, command) of each action bar line of Replay.inspect (#5461)."""
    import mc_check
    import replay
    import run
    shots, done = plan(out, times), []
    with tempfile.TemporaryDirectory() as tmp:
        world = os.path.join(tmp, "ShotWorld")
        if os.path.isdir(src):
            shutil.copytree(src, world)
        else:
            with contextlib.redirect_stdout(io.StringIO()):
                aoe2mc.convert(src, world)
        with open(os.path.join(world, "aoe2mc.json")) as f:
            data = json.load(f)
        _, (spawn, yaw) = mc_shot.world_version(world)
        x, y, z, *look = view or (spawn[0], spawn[1] + 2, spawn[2], yaw, 20)
        with run.Game(world, version or mc_check.DEFAULT_VERSION) as game, \
                mc_shot.Client(game.game_port, game.version, chat=True) as client:
            game.forceload()
            client.wait_join(lambda: client.name in game.command("list").split(":", 1)[-1])
            client.wait_loaded(game)
            game.command(f"gamemode spectator {client.name}")
            import combat
            combat.setup(game, data)
            r = replay.Replay(game, data, game.version, ai=True, camera=camera)
            if info is not None:
                inspect = r.inspect

                def logged(t, *a):
                    lines = inspect(t, *a)
                    info.extend((t, c) for c in lines)
                    return lines
                r.inspect = logged
            seen = []

            def poll(control):
                if camera and not seen:                        # a spectator from the start: the camera takes it
                    r.flush()                                  # (Replay.view_glide /spectate) and Replay.inspect
                    game.command(f"gamemode spectator {client.name}")   # reads its view (#5442)
                    seen.append(True)
                for s in due(shots, control["time"]):
                    r.flush()                                  # the commands up to now reach the server first
                    game.command(f"gamemode spectator {client.name}")   # the replay setup made the player a viewer
                    if camera != "player":                     # a tp ends the /spectate of the camera entity
                        game.command(f"tp {client.name} {x} {y} {z} {look[0]} {look[1]}")
                    time.sleep(settle)                         # the client draws the chunks of the camera
                    done.append(client.shot(s[1]))
                    shots.remove(s)
                    print(f"{replay.mmss(s[0])} {s[1]}", file=sys.stderr)
                if not shots:
                    raise Done

            try:
                r.run(speed, bar=True, poll=poll, log=None)
            except Done:
                pass
    return done


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("src", help="a record (.aoe2record) or a converted world of a record")
    ap.add_argument("out", help="PNG name: OUT_<M>m<SS>s.png for each time")
    ap.add_argument("--at-time", action="append", required=True, metavar="MM:SS", help="a game time of a shot (repeat)")
    ap.add_argument("--view", type=mc_shot.view_spec, metavar="X,Y,Z,YAW,PITCH", help="the camera (default: the spawn)")
    ap.add_argument("--speed", type=float, default=1.0, help="times the game speed (default 1)")
    ap.add_argument("--version", help="Minecraft version (default: mc_check.DEFAULT_VERSION)")
    ap.add_argument("--camera", choices=["auto", "player"], help="the camera mode of the replay (run.py --camera)")
    ap.add_argument("--info", metavar="FILE.json", help="log the info lines of Replay.inspect; exit 1: no unit line")
    a = ap.parse_args(argv)
    lines = [] if a.info else None
    for p in run_shots(a.src, a.out, a.at_time, a.view, a.speed, a.version, camera=a.camera, info=lines):
        print(p)
    if a.info:
        result = summary(lines)
        with open(a.info, "w") as f:
            json.dump(result, f, indent=1)
        print(f"info lines: {result['unit']} unit, {result['building']} building ({a.info})")
        return 0 if result["unit"] else 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
