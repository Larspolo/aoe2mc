"""Check of #1092: the civilization bonuses of the game program on Paper (game/run.py --play setup), with a real
client. Player 1 is Franks: Horse Collar is free (civs.COSTS), mounted units have 20 % more hit points from the Feudal
Age (civs.UNITS), foragers work 15 % faster (civs.WORK). The menu clicks go through train.open_menu and train.order,
as the player input. Usage: OUTDIR"""
import contextlib, io, json, os, re, shutil, sys, time, urllib.parse
ROOT = "/home/user/aoe2mc"
sys.path[:0] = [ROOT, os.path.join(ROOT, "game"), os.path.join(ROOT, "tools")]
import aoe2mc, scenarios, run, gather, combat, train, mc_shot, measure_gather, civs  # noqa
from AoE2ScenarioParser.datasets.buildings import BuildingInfo
from AoE2ScenarioParser.datasets.other import OtherInfo
from AoE2ScenarioParser.datasets.units import UnitInfo
from AoE2ScenarioParser.datasets.object_support import Civilization

out = sys.argv[1]
P1, GAIA = scenarios.PlayerId.ONE, scenarios.PlayerId.GAIA
scn = scenarios.new_scenario(40)
scn.player_manager.players[1].civilization = Civilization.FRANKS
um = scn.unit_manager
um.add_unit(P1, BuildingInfo.TOWN_CENTER.ID, x=8, y=8)
for name, x, y in [("BARRACKS", 15.5, 8.5), ("MILL", 9, 17)]:
    um.add_unit(P1, getattr(BuildingInfo, name).ID, x=x, y=y)
um.add_unit(P1, UnitInfo.SCOUT_CAVALRY.ID, x=20.5, y=20.5)
um.add_unit(P1, UnitInfo.VILLAGER_MALE.ID, x=11.5, y=19.5)
um.add_unit(GAIA, OtherInfo.FORAGE_BUSH.ID, x=12.5, y=21.5)
src, world = os.path.join(out, "franks.aoe2scenario"), os.path.join(out, "W")
scenarios.save(scn, src)
shutil.rmtree(world, ignore_errors=True)
with contextlib.redirect_stdout(io.StringIO()):
    aoe2mc.convert(src, world)
data = json.load(open(os.path.join(world, "aoe2mc.json")))
print("players", data.get("players"), flush=True)
uuid = {(o["player"], o["name"]): o["uuid"] for o in data["objects"] if o["kind"] == "unit" and "uuid" in o}
cell = {o["name"]: (o["footprint"][0] + 1, o["footprint"][1] + 1) for o in data["objects"]
        if o["kind"] == "building" and o["player"] == 1}
print("units", uuid, "buildings", cell, flush=True)
ME = "aoe2mc"
SCOUT = uuid[(1, "SCOUT_CAVALRY")]


def maxhp(u):
    m = re.search(r"is ([\d.]+)", game.command(f"attribute {u} minecraft:max_health get"))
    return float(m[1]) if m else None


menus = []
buf = io.StringIO()
with run.Game(world) as game:
    game.forceload()
    end = time.time() + 60
    while True:
        g = gather.Gather(game, data, cheats=True, log=buf).setup()
        if g.villagers:
            break
        assert time.time() < end
        time.sleep(1)
    combat.setup(game, data)
    send = game.command

    def spy(c):
        if c.startswith(f"aoe menu {ME} "):
            menus.append([urllib.parse.unquote(p) for p in c.split()[3:]])
        return send(c)
    game.command = g.command = spy
    for r in ("food", "wood", "gold", "stone"):
        g.stock[r] += 5000
        game.command(f"scoreboard players add {r.capitalize()} {g.board} 5000")
    with mc_shot.Client(game.game_port, game.version) as c:
        c.wait_join(lambda: ME in game.command("list"))
        game.command(f"gamemode adventure {ME}")

        def menu_of(b):
            menus.clear()
            train.open_menu(g, ME, cell[b])
            return menus[-1] if menus else []
        res = {"civ": civs.civ(g), "dark_mill": menu_of("MILL"), "dark_scout_hp": maxhp(SCOUT),
               "food_s": g.work_time("food"), "food_s_base": g.chop.get("food"), "wood_s": g.work_time("wood")}
        game.command(f"aoe menu-close {ME}")
        print("dark", json.dumps(res), flush=True)
        vil, = g.villagers
        g.select(vil)
        g.send(next(iter(g.map.bushes)))                                    # forage during the age up
        t0 = time.time()
        rect = train.open_menu(g, ME, cell["TOWN_CENTER"])
        assert train.order(g, ME, rect, train.ITEMS["FEUDAL_AGE"][0]) == 1
        game.command(f"aoe menu-close {ME}")
        g.run(400, until=lambda: "FEUDAL_AGE" in g.techs)
        res["feudal_s"] = round(time.time() - t0, 1)
        res["feudal_scout_hp"] = maxhp(SCOUT)
        res["feudal_mill"] = menu_of("MILL")
        time.sleep(4)
        c.shot(os.path.join(out, "mill-menu.png"))
        game.command(f"aoe menu-close {ME}")
        s0 = dict(g.stock)
        rect = train.open_menu(g, ME, cell["MILL"])
        res["collar_queued"] = train.order(g, ME, rect, train.ITEMS["HORSE_COLLAR"][0])
        res["collar_paid"] = {r: s0[r] - g.stock[r] for r in s0 if s0[r] != g.stock[r]}
        res["collar_price"] = train.price(g, "HORSE_COLLAR")
        game.command(f"aoe menu-close {ME}")
        res["forage"] = measure_gather.analyze([json.loads(x) for x in buf.getvalue().splitlines()])
        print("feudal", json.dumps(res), flush=True)
        g.select(SCOUT)
        x, y, z = map(float, re.findall(r"(-?[\d.]+)d", game.command(f"data get entity {SCOUT} Pos"))[:3])
        game.command(f"aoe stop {SCOUT}")
        game.command(f"tp {ME} {x} {y + 2} {z + 5} 180 20")
        time.sleep(6)
        res["bar"] = game.command("bossbar get aoe2mc:sel_p1 max") + " | " + game.command("bossbar get aoe2mc:sel_p1 value")
        c.shot(os.path.join(out, "scout-bar.png"))
        print("bar", res["bar"], flush=True)
        open(os.path.join(out, "log.jsonl"), "w").write(buf.getvalue())
        json.dump(res, open(os.path.join(out, "result.json"), "w"), indent=1, default=str)
