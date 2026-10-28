"""Check of #2660: the recap book and the end hotbar after "torpedo2" (Paper, real client). Usage: OUTDIR"""
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


with game_of("W1") as game:                                            # conquest with "torpedo2"
    g = start(game)
    with mc_shot.Client(game.game_port, game.version) as c:
        c.wait_join(lambda: ME in game.command("list"))
        game.command(f"gamemode adventure {ME}")
        look(game, g, c, *tc)
        time.sleep(6)
        g.run(8)
        c.shot(os.path.join(out, "hotbar-before.png"))
        res["before"] = game.command(f"data get entity {ME} Inventory")
        say(c, "torpedo2")
        g.run(30, until=lambda: g.ended)
        time.sleep(5)                                                  # the title goes
        c.shot(os.path.join(out, "hotbar-after.png"))
        res["ended"] = g.ended
        res["after"] = game.command(f"data get entity {ME} Inventory")
        c.key("1")
        time.sleep(1)
        c.xdo("click", 3)                                              # right click: open the book
        time.sleep(2)
        c.shot(os.path.join(out, "recap-1.png"))
        for i in (2, 3):
            c.key("Page_Down")
            time.sleep(1)
            c.shot(os.path.join(out, f"recap-{i}.png"))
json.dump(res, open(os.path.join(out, "result.json"), "w"), indent=1)
print(json.dumps(res)[:3000])
