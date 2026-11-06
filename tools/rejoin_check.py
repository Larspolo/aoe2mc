#!/usr/bin/env python3
"""
Quit and join a network game again with two real clients (#5907, the check of #5893): level 4 of the verify skill for
the bot of a dropped player (game/rejoin.py, run.LEFT).

Usage:
    python3 aoe2mc.py --random-map arabia --seed 1 OUTWorld
    python3 tools/rejoin_check.py OUTWorld OUTDIR [--quit 2:00] [--back 3:00] [--speed 4] [--beat N]

The tool copies the world and runs `run.main([WORLD, --play, --people 2])`. Client A ("alice", player 1) joins, then
client B ("bob", player 2) (tools/mc_shot.py). The tool sets both people "Ready" (the lobby page of #5508 needs a
click; this check is about the leave). B quits at --quit game time and joins again at --back. The tool samples the
Gather of player 2 (villager states, stock) at the quit, at the end of the bot time and after the join, and reads
the chat of client A, the server log and `execute if entity @a[name=bob,team=p2]`. OUTDIR gets result.json. Exit 0: all points are OK.
"""
import argparse
import collections
import json
import os
import re
import shutil
import sys
import tempfile
import threading
import time
import traceback

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path[:0] = [ROOT, HERE, os.path.join(ROOT, "game")]

import mc_shot  # noqa: E402
import recap  # noqa: E402
import rejoin  # noqa: E402
import run  # noqa: E402

ERROR = re.compile(r"Exception|ERROR\]|Caused by:")                    # as tools/play_check.py
OFFLINE = re.compile(r"minecraftservices\.com|Services are unavailable")
A, B = "alice", "bob"


def mmss(s):
    m, _, x = s.partition(":")
    return int(m) * 60 + float(x or 0)


def sample(g):
    """Villager ids, their states and the stock of Gather g."""
    vs = g.villagers
    return {"time": round(recap.game_time(g), 1), "stock": {k: int(v) for k, v in sorted(g.stock.items())},
            "villagers": sorted(map(str, vs)), "states": dict(collections.Counter(v.state for v in vs.values())),
            "gathering": sum(v.state not in ("idle",) for v in vs.values())}


def result(quit_, bot_end, back, left_lines, chat, team, errors):
    """{point: (ok, detail)} of the check."""
    lost = set(quit_["villagers"]) - set(back["villagers"])
    gained = {r: bot_end["stock"].get(r, 0) - quit_["stock"].get(r, 0) for r in quit_["stock"]}
    out = {"the leave matches run.LEFT": (bool(left_lines), "; ".join(left_lines[:2])),
           "A sees the bot line": (any(f"{B} left: a bot plays player 2" in x for x in chat), "; ".join(chat[-6:])),
           "A sees the back line": (any(f"{B} is back" in x for x in chat), "; ".join(chat[-6:])),
           "the bot gathers": (any(v > 0 for v in gained.values()) and bot_end["gathering"] > 0,
                               f"stock {quit_['stock']} -> {bot_end['stock']}, states {quit_['states']} -> {bot_end['states']}"),
           "B is on team p2": ("passed" in team, team),
           "B has the same villagers": (not lost, f"{len(quit_['villagers'])} at the quit, {len(back['villagers'])} "
                                                  f"after the join, lost {sorted(lost)}"),
           "B keeps the stock of the bot": (all(back["stock"].get(r, 0) >= bot_end["stock"].get(r, 0) - 200 for r in bot_end["stock"]),
                                            f"bot end {bot_end['stock']}, after the join {back['stock']}"),
           "no server errors": (not errors, "; ".join(e[:200] for e in errors[:5]))}
    return {k: (bool(ok), d) for k, (ok, d) in out.items()}


def chat_of(c):
    return [x.split("[CHAT]", 1)[1].strip() for x in c.text().splitlines() if "[CHAT]" in x]


def wait_time(g, t):
    while recap.game_time(g) < t:
        time.sleep(1)


def drive(games, a, report):
    try:
        while not games or not getattr(games[0], "game_port", None):
            time.sleep(1)
        game = games[0]
        while True:
            try:
                game.command("list")
                break
            except Exception:
                time.sleep(2)
        online = lambda n: n in game.command("list").split(":", 1)[-1]     # noqa: E731
        with mc_shot.Client(game.game_port, game.version, name=A, chat=True, world=a.copy) as ca:
            ca.wait_join(lambda: online(A))
            b = mc_shot.Client(game.game_port, game.version, name=B, world=a.copy).__enter__()
            b.wait_join(lambda: online(B))
            while not getattr(game, "wait", False):                        # start_on_join did not start yet
                time.sleep(0.5)
            while game.wait:
                game.ready = set(game.joined)                              # the "Ready" click of the lobby page
                time.sleep(0.5)
            time.sleep(2)
            g2 = rejoin.gathers(game.g)[2]
            print(json.dumps({"start": sample(g2)}), flush=True)
            wait_time(g2, a.quit)
            quit_ = sample(g2)
            b.__exit__(None, None, None)
            while online(B):
                time.sleep(0.5)
            print(json.dumps({"quit": quit_}), flush=True)
            wait_time(g2, a.back - 2)
            bot_end = sample(g2)
            print(json.dumps({"bot_end": bot_end}), flush=True)
            with mc_shot.Client(game.game_port, game.version, name=B) as b2:
                b2.wait_join(lambda: online(B))
                t = time.time()
                while 2 in vars(game.g).get("stand_ins", {}) and time.time() - t < 30:
                    time.sleep(0.5)
                time.sleep(5)
                back = sample(g2)
                print(json.dumps({"back": back}), flush=True)
                team = game.command(f"execute if entity @a[name={B},team=p2]")
                time.sleep(2)
                chat = chat_of(ca)
        log = game.server.log
        left = [x for x in log if run.LEFT.search(x) and B in x]
        errors = [x for x in log if ERROR.search(x) and not OFFLINE.search(x)]
        report.update(result(quit_, bot_end, back, left, chat, team, errors))
    except Exception:
        traceback.print_exc()
    finally:
        try:
            games[0].stop()
        finally:
            done(report, a.out)


def done(report, out):
    with open(os.path.join(out, "result.json"), "w") as f:
        json.dump(report, f, indent=1)
    bad = [k for k, (ok, _) in report.items() if not ok]
    for k, (ok, d) in report.items():
        print(f"{'OK  ' if ok else 'FAIL'} {k}: {d}", file=sys.stderr)
    print(json.dumps({"result": "OK" if report and not bad else "FAIL", "failed": bad or ["no result"] * (not report)}),
          flush=True)
    os._exit(0 if report and not bad else 1)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0].strip(),
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("world")
    ap.add_argument("out", help="the folder of result.json")
    ap.add_argument("--quit", type=mmss, default="2:00", help="game time of the quit of B (default 2:00)")
    ap.add_argument("--back", type=mmss, default="3:00", help="game time of the join of B (default 3:00)")
    ap.add_argument("--speed", type=float, default=4.0, help="times the Normal game speed (default 4)")
    ap.add_argument("--beat", type=int, metavar="N", help="beat the claim of ticket N every 10 minutes")
    a = ap.parse_args(argv)
    if a.beat:
        mc_shot.beat(a.beat)
    if not os.path.isfile(os.path.join(a.world, "level.dat")):
        sys.exit(f"no level.dat in {a.world}")
    os.makedirs(a.out, exist_ok=True)
    a.copy = os.path.join(tempfile.mkdtemp(), os.path.basename(os.path.normpath(a.world)))
    shutil.copytree(a.world, a.copy)                                   # the game changes the world
    games, report, init = [], {}, run.Game.__init__

    def game_init(self, *args, **kw):
        init(self, *args, **kw)
        games.append(self)

    run.Game.__init__ = game_init
    threading.Thread(target=drive, args=(games, a, report), daemon=True).start()
    r, _ = os.pipe()                                                   # run.console reads stdin: no EOF
    os.dup2(r, sys.stdin.fileno())
    run.main([a.copy, "--play", "--people", "2", "--speed", f"{a.speed:g}"])
    done(report, a.out)


if __name__ == "__main__":
    main()
