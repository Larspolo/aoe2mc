"""Check of #2753: the minimap of the game program (epic #2580) on Paper with a real 26.3 client. run.play runs the
game in a thread (the units, the buildings, the fog of war, the view square and the map table, as `game/run.py
--play`). Player 1 has a town center, a house, a villager and a militia; player 2 (no bot: its units stand) has a town
center far away, a militia in the sight of player 1 and a militia and a villager out of it. The client looks down at
the framed map of the map table, puts a flare and right clicks a pixel with the command stick. Usage: OUTDIR"""
import contextlib, io, json, math, os, re, shutil, sys, threading, time
ROOT = "/home/user/aoe2mc"
sys.path[:0] = [ROOT, os.path.join(ROOT, "game"), os.path.join(ROOT, "tools")]
import aoe2mc, scenarios, run, gather, map_table, flare, mc_shot  # noqa
from AoE2ScenarioParser.datasets.buildings import BuildingInfo
from AoE2ScenarioParser.datasets.units import UnitInfo

out = sys.argv[1]
P1, P2 = scenarios.PlayerId.ONE, scenarios.PlayerId.TWO
scn = scenarios.new_scenario(40)
um = scn.unit_manager
um.add_unit(P1, BuildingInfo.TOWN_CENTER.ID, x=8, y=8)
um.add_unit(P1, BuildingInfo.HOUSE.ID, x=14, y=5)
um.add_unit(P1, UnitInfo.VILLAGER_MALE.ID, x=4.5, y=14.5)
um.add_unit(P1, UnitInfo.MILITIA.ID, x=3.5, y=4.5)
um.add_unit(P2, BuildingInfo.TOWN_CENTER.ID, x=32, y=32)
um.add_unit(P2, UnitInfo.MILITIA.ID, x=13.5, y=11.5)                 # 6.5 tiles from the town center: in sight
um.add_unit(P2, UnitInfo.MILITIA.ID, x=30.5, y=8.5)                  # far: out of sight
um.add_unit(P2, UnitInfo.VILLAGER_MALE.ID, x=34.5, y=29.5)           # at its own town center: out of sight
src, world = os.path.join(out, "check.aoe2scenario"), os.path.join(out, "W")
scenarios.save(scn, src)
shutil.rmtree(world, ignore_errors=True)
with contextlib.redirect_stdout(io.StringIO()):
    aoe2mc.convert(src, world)
data = json.load(open(os.path.join(world, "aoe2mc.json")))
units = [o for o in data["objects"] if o["kind"] == "unit"]
ME, res = "aoe2mc", {"steps": []}


def step(name):
    res["steps"].append(time.strftime("%H:%M:%S ") + name)


def pos(game, u):
    return tuple(map(float, re.findall(r"(-?[\d.]+)d", game.command(f"data get entity {u} Pos"))[:3]))


def tile_line(game, x, z):
    return game.command(f"aoe minimap tile {int(x)} {int(z)} p1").strip()


with run.Game(world) as game, mc_shot.Client(game.game_port, game.version) as client:
    client.wait_join(lambda: ME in game.command("list").split(":", 1)[-1])
    time.sleep(5)
    th = threading.Thread(target=run.play, args=(game, world), kwargs={"seconds": 150}, daemon=True)
    step("play")
    th.start()
    end = time.time() + 120
    while not getattr(game, "g", None):
        assert time.time() < end, "no Gather"
        time.sleep(1)
    g = game.g
    time.sleep(6)                                                     # fog.tick and the map updates
    game.command(f"gamemode adventure {ME}")
    game.command(f"item replace entity {ME} hotbar.0 with minecraft:carrot_on_a_stick")
    client.key("1")
    tx, tz = map_table.cell(g) if map_table.cell(g) else (None, None)
    g.map.blocked.discard((tx, tz))
    ty = g.map.y(tx, tz)
    res["table"] = [tx, ty, tz]
    res["frame"] = game.command(f"data get entity @e[tag={map_table.TAG}.p1,limit=1] Item")
    hidden = set(vars(g).get("fog", {}).get("hidden", ()))
    res["units"] = []
    for o in units:
        p = pos(game, o["uuid"])
        res["units"].append({"name": o["name"], "player": o["player"], "pos": [round(v, 1) for v in p],
                             "hidden_for_p1": o["uuid"] in hidden, "tile": tile_line(game, p[0], p[2]),
                             "pixel": game.command(f"aoe minimap pixel {int(p[0])} {int(p[2])}").strip()})
    for o in data["objects"]:
        if o["kind"] == "building" and o["name"] in ("TOWN_CENTER", "HOUSE"):
            x0, z0, x1, z1 = o["footprint"]
            res.setdefault("buildings", []).append({"name": o["name"], "player": o["player"],
                                                    "tile": tile_line(game, (x0 + x1) // 2, (z0 + z1) // 2)})
    game.command(f"tp {ME} {tx + 0.5} {ty + 1} {tz + 3.5} 180 35")     # the map table from the side
    time.sleep(3)
    client.shot(os.path.join(out, "table_side.png"))
    item = '{id:"minecraft:filled_map",count:1,components:{"minecraft:map_id":0}}'
    for c in ("fill 78 119 78 82 119 82 stone", "fill 78 120 78 82 123 82 air",   # a clean frame of map 0 over the trees
              f"summon minecraft:glow_item_frame 80 120 80 {{Facing:1b,Fixed:1b,Item:{item}}}"):
        game.command(c)
    tx, ty, tz = 80, 119, 80
    step("frame")
    game.command(f"tp {ME} {tx + 0.5} {ty + 1} {tz + 0.5} 180 90")    # eye 1.62 above the frame, north up
    time.sleep(3)
    client.shot(os.path.join(out, "table.png"))
    step("kill the enemy in sight")
    for o in units:
        if o["player"] == 2 and o["name"] == "MILITIA" and o["uuid"] not in hidden:
            game.command(f"kill {o['uuid']}")
    v = next(iter(g.villagers.values()))
    fx, fz = int(v.pos[0]) + 12, int(v.pos[2]) + 12                   # a flare south-east of the villager
    step("flare")
    flare.put(g, ME, fx, g.map.y(fx, fz), fz)
    game.command(f"tp {ME} {tx + 0.5} {ty + 1} {tz + 0.5} 180 90")
    time.sleep(1.2)
    client.shot(os.path.join(out, "flare_a.png"))
    time.sleep(1.0)
    client.shot(os.path.join(out, "flare_b.png"))
    res["flare"] = [fx, fz]
    time.sleep(10)                                                    # the flare ends
    before = pos(game, v.uuid)
    g.choose({v.uuid}, v.uuid)
    game.command(f"tp {ME} {tx + 0.27} {ty + 1} {tz + 0.77} 0 90")    # the same look point as test_minimap_click.py
    time.sleep(2)
    step("click")
    client.xdo("click", "3")
    time.sleep(1.5)
    cx, cz = map_table.score(g, ME, map_table.X), map_table.score(g, ME, map_table.Z)
    res["click_block"] = [cx, cz]
    time.sleep(12)
    after = pos(game, v.uuid)
    res["villager"] = {"before": [round(x, 1) for x in before], "after": [round(x, 1) for x in after],
                       "goal": list(v.goal) if v.goal else None, "state": v.state,
                       "dist_to_click_before": round(math.dist((before[0], before[2]), (cx or 0, cz or 0)), 1),
                       "dist_to_click_after": round(math.dist((after[0], after[2]), (cx or 0, cz or 0)), 1)}
    game.command(f"tp {ME} {tx + 0.5} {ty + 1} {tz + 0.5} 180 90")
    time.sleep(3)
    client.shot(os.path.join(out, "after_click.png"))
    time.sleep(1)
    lf = os.path.join(game.folder, "logs", "latest.log")
    log = open(lf, errors="replace").read() if os.path.exists(lf) else ""
    res["log_errors"] = [x for x in log.splitlines() if re.search(r"ERROR|Exception|Unknown or incomplete|Incorrect argument", x)][:20]
    shutil.copy(lf, os.path.join(out, "latest.log")) if log else None
print(json.dumps(res, indent=1))
json.dump(res, open(os.path.join(out, "result.json"), "w"), indent=1)
