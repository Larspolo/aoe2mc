#!/usr/bin/env python3
"""
Take over a player of a recorded game with the real client and play on (#5702, the check of #5604): level 4 of the
verify skill for the takeover (game/takeover.py, run.py --replay --takeover P, the trigger of #5601).

Usage:
    python3 aoe2mc.py samples/de-64.3.aoe2record OUTWorld
    python3 tools/takeover_check.py OUTWorld OUTDIR [--from 5:00] [--player 1] [--trigger] [--minutes 2] [--speed 4] [--beat N]

The tool copies the world, runs `run.main([WORLD, --replay, --from T, --takeover P])` and joins the real client
(tools/mc_shot.py). --trigger: no --takeover; the client types `/trigger aoe_replay set N` in the chat after the join
(N = replay_input.TAKEOVER + P). After the takeover a thread samples the Gather of the person (`game.g`): the stock,
the population, the villagers and their jobs, the soldiers, the queues and the sites of the bots. It right clicks the
first own town center (Client.pick) and clicks "Villager" in its menu, then waits --minutes game minutes.
Each sample is one JSON line on stdout; the last line is the result. OUTDIR gets the screenshots (replay.png with
--trigger, t0.png, menu.png, t2.png) and result.json. Exit 0: all points of the result are OK.
"""
import argparse
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
import menu  # noqa: E402
import recap  # noqa: E402
import replay_input  # noqa: E402
import run  # noqa: E402
import takeover  # noqa: E402
import train  # noqa: E402

import units  # noqa: E402

ERROR = re.compile(r"Exception|ERROR\]|Caused by:")                    # as tools/play_check.py
OFFLINE = re.compile(r"minecraftservices\.com|Services are unavailable")   # no Mojang services in a cloud session
SETTLE = 10.0                                                          # real seconds after the takeover: the first sample


def trigger_value(player):
    """The value of `/trigger aoe_replay set N` that takes over player (#5601)."""
    return replay_input.TAKEOVER + player


def sample(g, bots=()):
    """The numbers of the person's Gather g and the site counts of the bot Gathers."""
    vs = g.villagers.values()
    return {"time": round(recap.game_time(g), 1), "stock": {k: int(v) for k, v in sorted(g.stock.items())},
            "pop": g.pop, "villagers": len(g.villagers), "idle": sum(v.state == "idle" for v in vs),
            "idle_jobs": sorted({f"{v.res}@{tuple(v.tree) if v.tree else None}" for v in vs if v.state == "idle"}),
            "soldiers": sorted(g.soldiers.values()), "queued": sum(len(q) for q in g.queues.values()),
            "age": sorted(t for t in g.techs if t.endswith("_AGE")), "bot_sites": {str(b.player): len(b.sites) for b in bots}}


def result(saved, first, last, queued, errors, start=0.0):
    """The points of the check from the save of the takeover (its player dict), the first and the last sample, the
    queue count after the click on "Villager", the server log errors and the game time of the save (start, seconds):
    {point: (ok, detail)}."""
    out = {"the clock goes on": (first["time"] >= start, f"save {start:g} s, game {first['time']:g} s at the start"),
           "stock of the replay": (all(first["stock"].get(r) == saved["stock"].get(r) for r in ("gold", "stone")),
                                   f"save {saved['stock']}, game {first['stock']}"),
           "age of the replay": (first["age"] == sorted(t for t in saved["techs"] if t.endswith("_AGE")),
                                 f"save {saved['techs']}, game {first['age']}"),
           "no Gaia bird joined": (not any(units.is_bird(n) for n in last["soldiers"]),
                                   f"pop {last['pop']}, villagers {last['villagers']}, soldiers {last['soldiers']}"),
           "the stock goes up": (any(last["stock"][r] > first["stock"][r] for r in ("food", "wood", "gold", "stone")),
                                 f"{first['stock']} -> {last['stock']}"),
           "food goes up": (last["stock"]["food"] > first["stock"]["food"] - 50 * max(0, last["villagers"] - first["villagers"]),
                            f"{first['stock']['food']} -> {last['stock']['food']}"),
           "the town center trains": (queued > first["queued"] and last["villagers"] > first["villagers"],
                                      f"queue {first['queued']} -> {queued}, villagers {first['villagers']} -> {last['villagers']}"),
           "a bot builds": (any(last["bot_sites"][p] > n for p, n in first["bot_sites"].items()),
                            f"sites {first['bot_sites']} -> {last['bot_sites']}"),
           "no server errors": (not errors, "; ".join(e[:200] for e in errors[:5]))}
    return {k: (bool(ok), d) for k, (ok, d) in out.items()}


def watch_clock(games, seen):
    """The game time of the person's Gather when the game after the takeover starts (the client can load later)."""
    while not games or getattr(games[0], "g", None) is None:
        time.sleep(0.1)
    seen["clock"] = round(recap.game_time(games[0].g), 1)


def drive(games, states, shown, a, out, report, seen):
    """The thread of the client: join, the trigger, the samples, the town center click and the screenshots."""
    try:
        while not games or not getattr(games[0], "game_port", None):
            time.sleep(1)
        game = games[0]
        while True:                                                    # RCON is up
            try:
                game.command("list")
                break
            except Exception:
                time.sleep(2)
        with mc_shot.Client(game.game_port, game.version, chat=True, world=a.copy) as c:
            c.wait_join(lambda: c.name in game.command("list").split(":", 1)[-1])
            c.wait_loaded(game)
            if a.trigger:
                time.sleep(5)
                c.shot(os.path.join(out, "replay.png"))
                c.key("t")
                time.sleep(1)
                c.xdo("type", "--delay", "50", f"/trigger aoe_replay set {trigger_value(a.player)}")
                time.sleep(1)
                c.key("Return")
            while getattr(game, "g", None) is None:
                time.sleep(0.5)
            g = game.g
            time.sleep(SETTLE)
            bots = [b.g for b in g.bots]
            first = sample(g, bots)
            print(json.dumps(first), flush=True)
            c.shot(os.path.join(out, "t0.png"))
            queued = first["queued"]
            if tcs := sorted(r for r, n in train.homes(g).items() if n == "TOWN_CENTER"):
                if feet := next((p for u in g.villagers if (p := g.pos(u))), None):
                    c.place(game, (tcs[0][0] + tcs[0][1]) // 2, int(feet[1]), tcs[0][3] + 6, yaw=180, wait=5.0)
                shown.pop(c.name, None)
                c.pick(g, tcs[0], dists=(10, 12, 14))
                time.sleep(2)
                if c.name in shown:
                    items = shown[c.name][1]
                    rows = max(i[0] for i in items) // 9 + 1
                    slot = next((i[0] for i in items if "Villager" in str(i[2])), 0)
                    c.shot(os.path.join(out, "menu.png"))
                    first["queued"] = sum(len(q) for q in g.queues.values())   # the queue trains on during the walk
                    c.click(*c.slot(slot, rows))
                    time.sleep(3)
                    queued = sum(len(q) for q in g.queues.values())
                    c.key("Escape")
            t0 = recap.game_time(g)
            while recap.game_time(g) - t0 < a.minutes * 60:
                time.sleep(5)
                print(json.dumps(sample(g, bots)), flush=True)
            last = sample(g, bots)
            c.shot(os.path.join(out, "t2.png"))
        errors = [x for x in game.server.log if ERROR.search(x) and not OFFLINE.search(x)]
        saved = states[-1]["players"][str(a.player)] if states else {"stock": {}, "techs": []}
        start = states[-1]["game_time"] if states else 0.0
        report.update(result(saved, first | {"time": seen.get("clock", first["time"])}, last, queued, errors, start))
    except Exception:
        traceback.print_exc()
    finally:
        try:
            games[0].stop()
        finally:
            done(report, out)


def done(report, out):
    """Write result.json, print the result line and end the process (run.main waits for stdin)."""
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
    ap.add_argument("world", help="a converted world of a recorded game (.aoe2record)")
    ap.add_argument("out", help="the folder of the screenshots and result.json")
    ap.add_argument("--from", dest="start", default="5:00", metavar="MM:SS", help="the replay starts here (default 5:00)")
    ap.add_argument("--player", type=int, default=1, help="the player to take over (default 1)")
    ap.add_argument("--trigger", action="store_true", help="take over with /trigger aoe_replay in the chat, not --takeover")
    ap.add_argument("--minutes", type=float, default=2.0, help="game minutes of play after the click (default 2)")
    ap.add_argument("--speed", type=float, default=4.0, help="times the Normal game speed (default 4)")
    ap.add_argument("--beat", type=int, metavar="N", help="beat the claim of ticket N every 10 minutes (#5783)")
    a = ap.parse_args(argv)
    if a.beat:
        mc_shot.beat(a.beat)
    if not os.path.isfile(os.path.join(a.world, "level.dat")):
        sys.exit(f"no level.dat in {a.world}")
    os.makedirs(a.out, exist_ok=True)
    a.copy = os.path.join(tempfile.mkdtemp(), os.path.basename(os.path.normpath(a.world)))
    shutil.copytree(a.world, a.copy)                                   # the game changes the world
    games, states, shown, report = [], [], {}, {}
    init, state, show = run.Game.__init__, takeover.state, menu.show

    def game_init(self, *args, **kw):
        init(self, *args, **kw)
        games.append(self)

    def keep_state(*args, **kw):
        states.append(d := state(*args, **kw))
        return d

    def keep_menu(g, player, title, items, handler):
        shown[player] = (title, items)
        return show(g, player, title, items, handler)

    run.Game.__init__, takeover.state, menu.show = game_init, keep_state, keep_menu
    seen = {}
    threading.Thread(target=watch_clock, args=(games, seen), daemon=True).start()
    threading.Thread(target=drive, args=(games, states, shown, a, a.out, report, seen), daemon=True).start()
    r, w = os.pipe()                                                   # run.console reads stdin: an open pipe, no EOF
    os.dup2(r, sys.stdin.fileno())
    run.main([a.copy, "--replay", "--from", a.start, "--speed", f"{a.speed:g}"]
             + ([] if a.trigger else ["--takeover", str(a.player)]))
    done(report, a.out)


if __name__ == "__main__":
    main()
