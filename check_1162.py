"""Check of #1162 (the script of #1109): the age up from the Dark Age to the Imperial Age on Paper (game/run.py --play setup), with a real
client. The menu clicks go through train.open_menu, train.order and build.open_menu, as the player input. The
buildings that an age needs are construction sites (build.near, build.found) that build.rise completes. Usage: OUTDIR"""
import contextlib, io, json, os, re, shutil, sys, time, urllib.parse
ROOT = "/home/user/aoe2mc"
sys.path[:0] = [ROOT, os.path.join(ROOT, "game"), os.path.join(ROOT, "tools")]
import aoe2mc, scenarios, run, gather, combat, train, build, mc_shot  # noqa
from AoE2ScenarioParser.datasets.buildings import BuildingInfo
from AoE2ScenarioParser.datasets.units import UnitInfo

out = sys.argv[1]
P1 = scenarios.PlayerId.ONE
scn = scenarios.new_scenario(48)
um = scn.unit_manager
um.add_unit(P1, BuildingInfo.TOWN_CENTER.ID, x=12, y=12)
um.add_unit(P1, BuildingInfo.BARRACKS.ID, x=19.5, y=12.5)
um.add_unit(P1, UnitInfo.VILLAGER_MALE.ID, x=16.5, y=8.5)
src, world = os.path.join(out, "ages.aoe2scenario"), os.path.join(out, "W")
scenarios.save(scn, src)
shutil.rmtree(world, ignore_errors=True)
with contextlib.redirect_stdout(io.StringIO()):
    aoe2mc.convert(src, world)
data = json.load(open(os.path.join(world, "aoe2mc.json")))
cell = {o["name"]: (o["footprint"][0] + 1, o["footprint"][1] + 1) for o in data["objects"]
        if o["kind"] == "building" and o["player"] == 1}
print("buildings", cell, flush=True)
ME = "aoe2mc"
MENUS = ("BARRACKS", "ARCHERY_RANGE", "STABLE", "BLACKSMITH")
menus, says = [], []
res = {"ages": {}, "menus": {}}
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
        if c.startswith(f"tellraw {ME} "):
            says.append(c.split(" ", 2)[2])
        return send(c)
    game.command = g.command = spy
    for r in ("food", "wood", "gold", "stone"):
        g.stock[r] += 5000
        game.command(f"scoreboard players add {r.capitalize()} {g.board} 5000")

    def put(name):
        """A complete building of name next to the town center: its site, then all the work."""
        if name not in build.COSTS:                                    # not in the build menu (the finding of check 1)
            build.COSTS[name], res["stand_in"] = {"stone": 650}, name
            build.BUILD_TIMES.setdefault(name, 200)
        rect = build.near(g, name, cell["TOWN_CENTER"], reach=30)
        site = build.found(g, name, rect)
        before = train.missing(g, NEXT) if NEXT else None              # the site is not complete yet
        if name == "CASTLE":                                           # #1162: the villager builds it
            t0 = time.time()
            g.build(site, set(g.villagers))
            g.run(600, until=lambda: site.get("done"))
            res["castle_build_s"] = (round(time.time() - t0, 1), site.get("done"), site["progress"])
            print("castle", res["castle_build_s"], flush=True)
        else:
            build.rise(g, site, build.BUILD_TIMES[name])
        x0, x1, z0, z1 = rect
        cell[name] = ((x0 + x1) // 2, (z0 + z1) // 2)
        print("built", name, rect, "while a site:", before, flush=True)
        return before

    def menu_of(b):
        menus.clear()
        if b == "BUILD":
            build.open_menu(g, ME)
        elif b in cell:
            train.open_menu(g, ME, cell[b])
        else:
            return None
        return menus[-1] if menus else []

    def snapshot(label):
        res["menus"][label] = {b: menu_of(b) for b in MENUS + ("BUILD",)}
        game.command(f"aoe menu-close {ME}")
        print(label, json.dumps(res["menus"][label]), flush=True)

    def research(age):
        """Click the age in the town center menu. Returns (queued, paid)."""
        s0 = dict(g.stock)
        says.clear()
        rect = train.open_menu(g, ME, cell["TOWN_CENTER"])
        tc = menus[-1] if menus else []
        n = train.order(g, ME, rect, train.ITEMS[age][0])
        game.command(f"aoe menu-close {ME}")
        return n, {r: s0[r] - g.stock[r] for r in s0 if s0[r] != g.stock[r]}, list(says), [i for i in tc if age.split("_")[0].title() in i]

    with mc_shot.Client(game.game_port, game.version) as c:
        c.wait_join(lambda: ME in game.command("list"))
        game.command(f"gamemode adventure {ME}")
        plan = [("FEUDAL_AGE", ["MILL"], "Dark"), ("CASTLE_AGE", ["ARCHERY_RANGE", "STABLE", "BLACKSMITH"], "Feudal"),
                ("IMPERIAL_AGE", ["CASTLE"], "Castle")]
        for age, need, now in plan:
            NEXT = age
            snapshot(now)
            row = {"refused": research(age)}
            print("refused", age, json.dumps(row), flush=True)
            row["while_site"] = [put(b) for b in need]
            row["queued"] = research(age)
            t0 = time.time()
            g.run(400, until=lambda: age in g.techs)
            row["real_s"], row["aoe2_s"] = round(time.time() - t0, 1), round(train.TRAIN_TIMES[age] / 1.7, 1)
            row["done"] = age in g.techs
            res["ages"][age] = row
            print(age, json.dumps(row), flush=True)
            if age == "CASTLE_AGE":
                menu_of("ARCHERY_RANGE")
                time.sleep(4)
                c.shot(os.path.join(out, "archery-castle.png"))
                game.command(f"aoe menu-close {ME}")
        NEXT = None
        snapshot("Imperial")
        menu_of("BUILD")
        time.sleep(4)
        c.shot(os.path.join(out, "build-imperial.png"))
        game.command(f"aoe menu-close {ME}")
        x, z = cell["CASTLE"]
        game.command(f"tp {ME} {x} {g.map.y(x, z) + 14} {z + 22} 180 30")
        time.sleep(6)
        c.shot(os.path.join(out, "town-imperial.png"))
        res["sidebar"] = game.command(f"scoreboard objectives list")
        json.dump(res, open(os.path.join(out, "result.json"), "w"), indent=1, default=str)
        print("end", flush=True)
