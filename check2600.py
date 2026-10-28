"""Check #2600: a game of the game program with a start age and start resources, in Minecraft with a real client."""
import json
import os
import sys
import time

sys.path[:0] = ["game", "tools", "."]
import build  # noqa: E402
import gather  # noqa: E402
import mc_shot  # noqa: E402
import run  # noqa: E402
import train  # noqa: E402

W, OUT = sys.argv[1], sys.argv[2]
os.makedirs(OUT, exist_ok=True)


def look(game, g):
    tc = next(o for o in g.data["objects"] if o["kind"] == "building" and o["name"] == "TOWN_CENTER" and o["player"] == 1)
    x0, z0, x1, z1 = tc["footprint"]
    cx, cz = (x0 + x1) / 2, (z0 + z1) / 2
    y = g.map.y(int(cx), int(cz)) or 64
    game.command("gamemode spectator aoe2mc")
    game.command(f"tp aoe2mc {cx} {y + 22} {cz + 22} 180 40")
    return (int(cx), int(cz))


report = {}
for name, settings in (("castle_high", dict(age="castle", resources="high")),
                       ("dark_standard", dict(age="dark", resources="standard"))):
    with run.Game(W) as game, mc_shot.Client(game.game_port, game.version) as c:
        c.wait_join(lambda: "aoe2mc" in game.command("list").split(":", 1)[-1])
        time.sleep(5)
        g = run.play(game, W, seconds=2, **settings)
        cell = look(game, g)
        r = {"stock": {k: round(v) for k, v in sorted(g.stock.items())}, "ages": build.ages(g),
             "age_techs": [t for t in build.AGE_TECHS if t in g.techs], "pop_limit": train.limit(g),
             "tc_menu": [n for n in train.trains(g, "TOWN_CENTER") if n in build.AGE_TECHS],
             "level": gather.LEVELS.get(settings["resources"])}
        nxt = build.AGE_TECHS[min(r["ages"], len(build.AGE_TECHS) - 1)]
        r["queue " + nxt] = train.queue(g, "aoe2mc", cell, nxt) is not None
        if r["ages"]:
            r["queue " + build.AGE_TECHS[r["ages"] - 1]] = train.queue(g, "aoe2mc", cell, build.AGE_TECHS[r["ages"] - 1]) is not None
        r["stock after queue"] = {k: round(v) for k, v in sorted(g.stock.items())}
        g.run(3)
        look(game, g)
        time.sleep(6)
        c.shot(os.path.join(OUT, f"{name}.png"))
        report[name] = r
        print(name, json.dumps(r), file=sys.stderr)
with open(os.path.join(OUT, "report.json"), "w") as f:
    json.dump(report, f, indent=1, default=str)
print(json.dumps(report, indent=1, default=str))
