"""Check of #965: the Feudal Age technologies of the game program on Paper (game/run.py --play setup), with a real
client. The menu clicks go through train.open_menu and train.order, as the player input. Usage: OUTDIR"""
import contextlib, io, json, os, re, shutil, sys, time, urllib.parse
ROOT = "/home/user/aoe2mc"
sys.path[:0] = [ROOT, os.path.join(ROOT, "game"), os.path.join(ROOT, "tools")]
import aoe2mc, scenarios, run, gather, combat, train, mc_shot  # noqa
from AoE2ScenarioParser.datasets.buildings import BuildingInfo
from AoE2ScenarioParser.datasets.other import OtherInfo
from AoE2ScenarioParser.datasets.units import UnitInfo

out = sys.argv[1]
P1, P2, GAIA = scenarios.PlayerId.ONE, scenarios.PlayerId.TWO, scenarios.PlayerId.GAIA
scn = scenarios.new_scenario(40)
um = scn.unit_manager
um.add_unit(P1, BuildingInfo.TOWN_CENTER.ID, x=8, y=8)
for name, x, y in [("BARRACKS", 15.5, 8.5), ("BLACKSMITH", 8.5, 15.5), ("STABLE", 15.5, 15.5),
                   ("MINING_CAMP", 21, 15), ("ARCHERY_RANGE", 21.5, 8.5)]:
    um.add_unit(P1, getattr(BuildingInfo, name).ID, x=x, y=y)
for name, x, y in [("MILITIA", 3.5, 21.5), ("ARCHER", 13.5, 21.5), ("SCOUT_CAVALRY", 8.5, 33.5)]:   # apart: #965
    um.add_unit(P1, getattr(UnitInfo, name).ID, x=x, y=y)
um.add_unit(P1, UnitInfo.VILLAGER_MALE.ID, x=12.5, y=4.5)
um.add_unit(P2, UnitInfo.MILITIA.ID, x=32.5, y=32.5)
um.add_unit(GAIA, OtherInfo.STONE_MINE.ID, x=24.5, y=16.5)
src, world = os.path.join(out, "feudal.aoe2scenario"), os.path.join(out, "W")
scenarios.save(scn, src)
shutil.rmtree(world, ignore_errors=True)
with contextlib.redirect_stdout(io.StringIO()):
    aoe2mc.convert(src, world)
data = json.load(open(os.path.join(world, "aoe2mc.json")))
uuid = {(o["player"], o["name"]): o["uuid"] for o in data["objects"] if o["kind"] == "unit" and "uuid" in o}
cell = {o["name"]: (o["footprint"][0] + 1, o["footprint"][1] + 1) for o in data["objects"]
        if o["kind"] == "building" and o["player"] == 1}
print("units", uuid, "buildings", cell, flush=True)
ME = "aoe2mc"


def health(u):
    r = game.command(f"data get entity {u} Health")
    m = re.search(r"([\d.]+)f", r)
    if not m:
        print("health?", u, r, game.command(f"data get entity {u} id"), flush=True)
    return float(m[1]) if m else None


def maxhp(u):
    m = re.search(r"is ([\d.]+)", game.command(f"attribute {u} minecraft:max_health get"))
    return float(m[1]) if m else None


def hit(u):
    """One melee hit of the militia of player 2 (AoE2 attack 4) on unit u: the lost hit points."""
    time.sleep(3)                                                   # its reload
    h = health(u)
    game.command(f"damage {u} 1 minecraft:mob_attack by {uuid[(2, 'MILITIA')]}")
    time.sleep(0.3)
    game.command(f"aoe stop {u}")
    h2 = health(u)
    print("hit", u, h, h2, flush=True)
    return round(h - h2, 2) if h is not None and h2 is not None else None


menus = []
with run.Game(world) as game:
    game.forceload()
    end = time.time() + 60
    while True:
        g = gather.Gather(game, data, cheats=True).setup()
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
    game.command = g.command = spy if hasattr(g, "command") else spy
    for r in ("food", "wood", "gold", "stone"):
        g.stock[r] += 5000
        game.command(f"scoreboard players add {r.capitalize()} {g.board} 5000")
    with mc_shot.Client(game.game_port, game.version) as c:
        c.wait_join(lambda: ME in game.command("list"))
        game.command(f"gamemode adventure {ME}")
        rows = {}

        def menu_of(b):
            menus.clear()
            train.open_menu(g, ME, cell[b])
            return menus[-1] if menus else []
        dark = {b: menu_of(b) for b in ("BARRACKS", "BLACKSMITH", "STABLE", "MINING_CAMP")}
        print("dark menus", json.dumps(dark), flush=True)
        game.command(f"aoe menu-close {ME}")
        before = {"archer_hit": hit(uuid[(1, "ARCHER")]), "scout_hit": hit(uuid[(1, "SCOUT_CAVALRY")]),
                  "scout_hp": maxhp(uuid[(1, "SCOUT_CAVALRY")]), "militia_hp": maxhp(uuid[(1, "MILITIA")]),
                  "stone_s": g.work_time("stone"), "militia_name": game.command(f"data get entity {uuid[(1, 'MILITIA')]} CustomName")}
        print("before", json.dumps(before), flush=True)
        # Feudal Age through the town center menu (slot 2)
        t0 = time.time()
        rect = train.open_menu(g, ME, cell["TOWN_CENTER"])
        assert train.order(g, ME, rect, train.ITEMS["FEUDAL_AGE"][0]) == 1
        g.run(400, until=lambda: "FEUDAL_AGE" in g.techs)
        print("feudal", round(time.time() - t0, 1), "s", flush=True)
        feudal = {b: menu_of(b) for b in ("BARRACKS", "BLACKSMITH", "STABLE", "MINING_CAMP")}
        print("feudal menus", json.dumps(feudal), flush=True)
        menu_of("BLACKSMITH")
        time.sleep(4)
        c.shot(os.path.join(out, "menu.png"))
        game.command(f"aoe menu-close {ME}")
        techs = [("PADDED_ARCHER_ARMOR", "BLACKSMITH"), ("SCALE_BARDING_ARMOR", "BLACKSMITH"), ("STONE_MINING", "MINING_CAMP"),
                 ("BLOODLINES", "STABLE"), ("MAN_AT_ARMS_UPGRADE", "BARRACKS")]
        for t, b in techs:
            s0 = dict(g.stock)
            rect = train.open_menu(g, ME, cell[b])
            n = train.order(g, ME, rect, train.ITEMS[t][0])
            cost = {r: s0[r] - g.stock[r] for r in s0 if s0[r] != g.stock[r]}
            game.command(f"aoe menu-close {ME}")
            t1 = time.time()
            g.run(200, until=lambda: t in g.techs)
            rows[t] = {"queued": n, "cost": cost, "real_s": round(time.time() - t1, 1), "done": t in g.techs}
            print(t, json.dumps(rows[t]), flush=True)
        after = {"archer_hit": hit(uuid[(1, "ARCHER")]), "scout_hit": hit(uuid[(1, "SCOUT_CAVALRY")]),
                 "scout_hp": maxhp(uuid[(1, "SCOUT_CAVALRY")]), "militia_hp": maxhp(uuid[(1, "MILITIA")]),
                 "stone_s": g.work_time("stone"), "militia_name": game.command(f"data get entity {uuid[(1, 'MILITIA')]} CustomName"),
                 "soldiers": g.soldiers, "barracks_trains": train.trains(g, "BARRACKS")}
        print("after", json.dumps(after), flush=True)
        stats_cmds = [x for x in g.__dict__.get("_log", [])]
        x, y, z = map(float, re.findall(r"(-?[\d.]+)d", game.command(f"data get entity {uuid[(1, 'MILITIA')]} Pos"))[:3])
        game.command(f"aoe stop {uuid[(1, 'MILITIA')]}")
        game.command(f"tp {ME} {x} {y + 2} {z + 5} 180 20")
        time.sleep(6)
        c.shot(os.path.join(out, "man_at_arms.png"))
        json.dump({"dark": dark, "feudal": feudal, "before": before, "after": after, "rows": rows},
                  open(os.path.join(out, "result.json"), "w"), indent=1, default=str)
