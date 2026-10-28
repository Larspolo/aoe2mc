"""Check #2381: save, stop, load a game of the game program in Minecraft with a real client."""
import json
import math
import os
import sys
import time

sys.path[:0] = ["game", "tools", "."]
import build  # noqa: E402
import mc_shot  # noqa: E402
import run  # noqa: E402
import savegame  # noqa: E402
import train  # noqa: E402

W, OUT = sys.argv[1], sys.argv[2]
os.makedirs(OUT, exist_ok=True)


def snap(g):
    return {"stock": {k: round(v) for k, v in sorted(g.stock.items())}, "pop": g.pop, "techs": sorted(g.techs),
            "queues": {str(k): v for k, v in g.queues.items()},
            "sites": [(s["name"], list(s["footprint"]), round(s["progress"], 2), bool(s.get("done"))) for s in g.sites],
            "villagers": {u[:8]: (v.state, v.res, round(v.load, 1), v.job) for u, v in sorted(g.villagers.items())}}


def look(game, g):
    """Put the player above the town center, looking down at it."""
    tc = next(o for o in g.data["objects"] if o["kind"] == "building" and o["name"] == "TOWN_CENTER" and o["player"] == 1)
    x0, z0, x1, z1 = tc["footprint"]
    cx, cz = (x0 + x1) / 2, (z0 + z1) / 2
    y = g.map.y(int(cx), int(cz)) or 64
    game.command("gamemode spectator aoe2mc")
    game.command(f"tp aoe2mc {cx} {y + 22} {cz + 22} 180 40")
    return (int(cx), int(cz)), tc


def joined(game):
    return lambda: "aoe2mc" in game.command("list").split(":", 1)[-1]


report = {}
with run.Game(W) as game, mc_shot.Client(game.game_port, game.version) as c:
    c.wait_join(joined(game))
    time.sleep(5)
    g = run.play(game, W, seconds=2)
    cell, tc = look(game, g)
    print("queue", train.queue(g, "aoe2mc", cell), train.queue(g, "aoe2mc", cell), file=sys.stderr)
    vs = sorted(g.villagers)
    x0, z0, x1, z1 = tc["footprint"]
    site = None
    for dx in range(0, 40, 4):                                       # a free house place next to the town center
        for r in [(x1 + 4 + dx, x1 + 12 + dx, z0, z0 + 8), (x0 - 12 - dx, x0 - 4 - dx, z0, z0 + 8),
                  (x0, x0 + 8, z1 + 4 + dx, z1 + 12 + dx)]:
            if site is None and build.free(g, r):
                site = build.found(g, "HOUSE", r)
    print("site", site and site["footprint"], file=sys.stderr)
    g.build(site, {vs[0]})
    trees = sorted(g.map.trees, key=lambda t: math.dist(t, (cell[0] / g.map.T, cell[1] / g.map.T)))
    g.send(trees[0], set(vs[1:3]))
    g.run(12)
    look(game, g)
    time.sleep(6)
    report["before"] = snap(g)
    c.shot(os.path.join(OUT, "before.png"))
    path = savegame.save(g, "aoe2mc")
    report["save"] = path
    report["saved"] = snap(g)
print(json.dumps(report, indent=1), file=sys.stderr)

run.restore(os.path.join(path, "world"), W)                          # what --load does before the server starts
state = savegame.read(path)
with run.Game(W) as game, mc_shot.Client(game.game_port, game.version) as c:
    c.wait_join(joined(game))
    time.sleep(5)
    g = run.play(game, W, seconds=1, state=state)
    report["loaded"] = snap(g)
    look(game, g)
    g.run(30)
    look(game, g)
    time.sleep(6)
    report["after"] = snap(g)
    c.shot(os.path.join(OUT, "after.png"))
with open(os.path.join(OUT, "report.json"), "w") as f:
    json.dump(report, f, indent=1)
print(json.dumps(report, indent=1))
