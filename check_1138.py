"""Check of #1138: the end of a game of the game program on Paper (game/run.py --play --cheats setup), with a real
client. Game 1: the player types "torpedo2" in the chat, conquest.tick ends the game with "Victory". Game 2: a complete
WONDER of player 1 (build.found, build.rise), wonder.tick shows its boss bar; the countdown is cut to 20 game seconds
(the real timer is 200 years = 1000 game seconds), then "Victory". Usage: OUTDIR"""
import contextlib, io, json, os, shutil, sys, time
ROOT = "/home/user/aoe2mc"
sys.path[:0] = [ROOT, os.path.join(ROOT, "game"), os.path.join(ROOT, "tools")]
import aoe2mc, scenarios, run, gather, combat, build, mc_shot  # noqa
from AoE2ScenarioParser.datasets.buildings import BuildingInfo
from AoE2ScenarioParser.datasets.units import UnitInfo

out = sys.argv[1]
P1, P2 = scenarios.PlayerId.ONE, scenarios.PlayerId.TWO
scn = scenarios.new_scenario(48)
um = scn.unit_manager
um.add_unit(P1, BuildingInfo.TOWN_CENTER.ID, x=12, y=12)
um.add_unit(P1, UnitInfo.VILLAGER_MALE.ID, x=16.5, y=8.5)
um.add_unit(P2, BuildingInfo.BARRACKS.ID, x=36.5, y=36.5)
um.add_unit(P2, UnitInfo.VILLAGER_MALE.ID, x=32.5, y=32.5)
src, base = os.path.join(out, "end.aoe2scenario"), os.path.join(out, "W0")
scenarios.save(scn, src)
shutil.rmtree(base, ignore_errors=True)
with contextlib.redirect_stdout(io.StringIO()):
    aoe2mc.convert(src, base)
data = json.load(open(os.path.join(base, "aoe2mc.json")))
tc = next((o["footprint"][0] + 1, o["footprint"][1] + 1) for o in data["objects"]
          if o["kind"] == "building" and o["name"] == "TOWN_CENTER")
ME = "aoe2mc"
res = {}


def game_of(name):
    world = os.path.join(out, name)
    shutil.rmtree(world, ignore_errors=True)
    shutil.copytree(base, world)
    return run.Game(world)


def start(game):
    game.forceload()
    end = time.time() + 60
    while True:
        g = gather.Gather(game, data, cheats=True).setup()
        if g.villagers:
            break
        assert time.time() < end
        time.sleep(1)
    combat.setup(game, data)
    return g


def say(c, text):
    c.key("t")
    time.sleep(1)
    c.xdo("type", "--delay", 50, text)
    c.key("Return")
    time.sleep(1)


def look(game, g, c, x, z):
    game.command(f"tp {ME} {x} {g.map.y(x, z) + 12} {z + 18} 180 30")


with game_of("W1") as game:                                            # game 1: conquest
    g = start(game)
    with mc_shot.Client(game.game_port, game.version) as c:
        c.wait_join(lambda: ME in game.command("list"))
        game.command(f"gamemode adventure {ME}")
        look(game, g, c, *tc)
        time.sleep(6)                                                  # the chat toast goes
        g.run(8)                                                       # conquest.tick sees both players
        res["seen"] = sorted(vars(g).get("conquest_seen", ()))
        say(c, "torpedo2")
        t0 = time.time()
        g.run(30, until=lambda: g.ended)
        for i, w in enumerate((0, 0.5, 1.0)):                         # the title fades in and out in about 4 s
            time.sleep(w)
            c.shot(os.path.join(out, f"conquest-victory-{i}.png"))
        res["conquest"] = {"ended": g.ended, "s": round(time.time() - t0, 1),
                           "defeated": sorted(vars(g).get("defeated", ())),
                           "p2_left": game.command("execute if entity @e[tag=aoe2mc.p2]"),
                           "chat": [ln for ln in c.text().splitlines() if "[CHAT]" in ln][-5:]}
        print("conquest", json.dumps(res["conquest"]), flush=True)

with game_of("W2") as game:                                            # game 2: wonder
    g = start(game)
    for r, n in build.COSTS["WONDER"].items():
        g.stock[r] += n
        game.command(f"scoreboard players add {r.capitalize()} {g.board} {n}")
    with mc_shot.Client(game.game_port, game.version) as c:
        c.wait_join(lambda: ME in game.command("list"))
        game.command(f"gamemode adventure {ME}")
        rect = build.near(g, "WONDER", tc, reach=30)
        site = build.found(g, "WONDER", rect)
        build.rise(g, site, build.BUILD_TIMES["WONDER"])
        x0, x1, z0, z1 = rect
        x = (x0 + x1) // 2                                             # north of the wonder: the town center is south
        game.command(f"tp {ME} {x} {g.map.y(x, z0 - 16) + 10} {z0 - 16} 0 25")
        time.sleep(6)                                                  # the chat toast goes
        g.run(10, until=lambda: vars(g).get("wonders"))
        g.run(6)
        c.shot(os.path.join(out, "wonder-bar.png"))
        res["wonder"] = {"rect": rect, "timers": {u: dict(t) for u, t in vars(g).get("wonders", {}).items()},
                         "bar": game.command("bossbar get aoe2mc:wonder_p1 value"),
                         "bars": game.command("bossbar list")}
        for t in g.wonders.values():
            t["left"] = 20.0                                           # cut the 1000 game seconds to 20
        t0 = time.time()
        shots = 0
        while not g.ended and time.time() - t0 < 60:
            g.run(4, until=lambda: g.ended)
            if not g.ended and shots < 1:
                c.shot(os.path.join(out, "wonder-bar-low.png"))
                res["wonder"]["bar_low"] = game.command("bossbar get aoe2mc:wonder_p1 value")
                shots += 1
        for i, w in enumerate((0, 0.5, 1.0)):
            time.sleep(w)
            c.shot(os.path.join(out, f"wonder-victory-{i}.png"))
        time.sleep(8)
        res["wonder"]["bars_after"] = game.command("bossbar list")
        c.shot(os.path.join(out, "wonder-after.png"))
        res["wonder"] |= {"ended": g.ended, "s": round(time.time() - t0, 1),
                          "chat": [ln for ln in c.text().splitlines() if "[CHAT]" in ln][-5:]}
        print("wonder", json.dumps(res["wonder"], default=str), flush=True)
json.dump(res, open(os.path.join(out, "result.json"), "w"), indent=1, default=str)
print("end", flush=True)
