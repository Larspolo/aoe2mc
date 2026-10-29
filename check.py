"""Check #4123: the unique buildings on Paper with a real client."""
import contextlib, io, json, os, re, sys, time
ROOT = "/home/user/aoe2mc"
sys.path[:0] = [ROOT, ROOT + "/tools", ROOT + "/game", ROOT + "/tests"]
import aoe2mc, scenarios, mc_shot
from AoE2ScenarioParser.datasets.units import UnitInfo
from game import build, combat, gather, run, train
from test_damage import health

OUT = sys.argv[1]
os.makedirs(OUT, exist_ok=True)
DOWN = (0.0, 90.0)
scn = scenarios.new_scenario(48)
for i in range(3):
    scn.unit_manager.add_unit(scenarios.PlayerId.ONE, UnitInfo.VILLAGER_MALE.ID, x=2.5 + i, y=2.5)
src = OUT + "/u.aoe2scenario"
scenarios.save(scn, src)
with contextlib.redirect_stdout(io.StringIO()):
    aoe2mc.convert(src, OUT + "/W")
data0 = json.load(open(OUT + "/W/aoe2mc.json"))
R = {}


def log(*a):
    print(*a, flush=True)
    R.setdefault("log", []).append(" ".join(map(str, a)))


def count(game):
    log("raw", game.command("execute if entity @e[type=!player]"), len(game.command("data get entity @e[type=villager,limit=1] UUID")))
    m = re.search(r"Count: (\d+)", game.command("execute if entity @e[type=!player]"))
    return int(m.group(1)) if m else 0


def run_for(g, secs):
    for _ in range(int(secs / (g.tick * gather.NORMAL))):
        g.step()
        time.sleep(g.tick)


with run.Game(OUT + "/W") as game, mc_shot.Client(game.game_port, game.version) as cl:
    cl.wait_join(lambda: "aoe2mc" in game.command("list").split(":", 1)[-1])
    game.forceload()
    game.command("gamemode creative aoe2mc")
    time.sleep(5)
    plan = [("SICILIANS", "DONJON", 40), ("POLES", "FOLWARK", 40), ("BULGARIANS", "KREPOST", 40),
            ("PORTUGUESE", "FEITORIA", 40), ("KHITANS", "PASTURE", 110)]
    for civ, name, x in plan:
        data = json.loads(json.dumps(data0))
        data["players"]["1"]["civ"] = civ
        g = gather.Gather(game, data, tick=0.25, start={}).setup()
        g.techs |= {"FEUDAL_AGE", "CASTLE_AGE", "IMPERIAL_AGE"}
        for r in ("food", "wood", "gold", "stone"):
            g.earn(r, 5000 - g.stock[r])
        game.command(f"tp aoe2mc {x} {g.map.y(x, 120) + 2} 120 180 30")
        time.sleep(2)
        build.open_menu(g, "aoe2mc")
        time.sleep(3)
        cl.xdo("mousemove", *cl.slot(build.MENU.index(name), 5))
        time.sleep(1)
        cl.shot(f"{OUT}/menu_{civ.lower()}.png")
        game.command("aoe menu-close aoe2mc")
        z = 100
        site = build.place(g, "aoe2mc", name, (x + 0.5, g.map.y(x, z) + 10, z + 0.5), gather.direction(*DOWN))
        assert site, name
        assert build.rise(g, site, build.BUILD_TIMES[name])
        x0, x1, z0, z1 = site["footprint"]
        cx, cz = (x0 + x1) / 2, (z0 + z1) / 2
        log(civ, name, "complete:", site["progress"] == 1, "footprint", site["footprint"])
        if name == "FEITORIA":
            before = dict(g.stock)
            run_for(g, 60)
            log("Feitoria stock before", before, "after 60 game s", dict(g.stock),
                "diff", {k: g.stock[k] - before[k] for k in ("food", "wood", "gold", "stone")})
        if name == "FOLWARK":
            food = g.stock["food"]
            farm = build.place(g, "aoe2mc", "FARM", (x1 + 6.5, g.map.y(x1 + 6, int(cz)) + 10, cz + 0.5), gather.direction(*DOWN))
            build.rise(g, farm, build.BUILD_TIMES["FARM"])
            tile = (farm["footprint"][0] // 4 + 1, farm["footprint"][2] // 4 + 1)
            log("Folwark: farm at", farm["footprint"], "food before", food, "after", g.stock["food"],
                "farm food left", g.map.farms.get(tile), "of", gather.FARM_FOOD)
        if name == "PASTURE":
            tile = (x0 // 4 + 1, z0 // 4 + 1)
            us = list(g.villagers)[:3]
            g.selected = set(us)
            g.send(tile)
            log("Pasture: herders", [g.villagers[u].tree == tile for u in us], "farm food", g.map.farms.get(tile))
            food = g.stock["food"]
            run_for(g, 120)
            log("Pasture: food after 120 game s", g.stock["food"] - food, "states",
                [g.villagers[u].state for u in us], "left", g.map.farms.get(tile))
        if name in ("DONJON", "KREPOST"):
            rect = next(r for r, n in train.homes(g).items() if n == name)
            log(name, "trains", train.trains(g, name))
            unit = "SERJEANT" if name == "DONJON" else "KONNIK"
            h = build.place(g, "aoe2mc", "HOUSE", (x0 - 9.5, g.map.y(x0 - 10, z0) + 10, z0 + 0.5), gather.direction(*DOWN))
            log("house", bool(h) and build.rise(g, h, build.BUILD_TIMES["HOUSE"]), "limit", train.limit(g))
            n0 = count(game)
            ok = train.queue(g, "aoe2mc", (x0, z0), unit)
            run_for(g, train.TRAIN_TIMES[unit] + 5)
            log(name, "queued", unit, bool(ok), "queue left", g.queues.get(rect), "entities", n0, "->", count(game), "objects", sum(o.get("name") == unit for o in g.data["objects"]))
            game.command("team add p2")
            ey = g.map.y(x1 + 8, int(cz))
            game.command(f'summon zombie {x1 + 8.5} {ey} {cz} {{NoAI:1b,Tags:["e{name}"]}}')
            game.command(f"team join p2 @e[tag=e{name}]")
            game.command(combat.stats_command(f"@e[tag=e{name},limit=1]", "MILITIA"))
            game.command(f"aoe stats @e[tag=e{name},limit=1] 1000 4 0 1 0 infantry - 20")
            game.command("time set midnight")
            time.sleep(10)
            log(name, "enemy health 1000 ->", health(game, f"e{name}"))
        game.command("time set noon")
        game.command("kill @e[type=zombie]")
        game.command(f"tp aoe2mc {cx + 16} {g.map.y(x1, z1) + 8} {cz + 16} 135 15")
        time.sleep(6)
        cl.shot(f"{OUT}/built_{name.lower()}.png")
        g.stop() if hasattr(g, "stop") else None
json.dump(R, open(OUT + "/result.json", "w"), indent=1)
