"""Check #1666: a loaded transport ship that the player sends inland with real right clicks of the client (xdotool)
unloads its units on the shore next to the ship, and the units walk on to the clicked cell (#1652). The player holds
the command stick in adventure mode; Gather.run reads the clicks (the statistic) and casts the ray of the player view."""
import contextlib, io, json, math, sys, time
ROOT = sys.argv[2]
sys.path[:0] = [ROOT, ROOT + "/tools", ROOT + "/game"]
import aoe2mc, scenarios, mc_shot
from AoE2ScenarioParser.datasets.buildings import BuildingInfo
from AoE2ScenarioParser.datasets.units import UnitInfo
import run, gather, combat

OUT = sys.argv[1]
scn = scenarios.new_scenario(48)
for t in scn.map_manager.terrain:                                   # a sea between a west and an east shore
    if 14 <= t.x < 34:
        t.terrain_id = scenarios.TerrainId.WATER_DEEP
um = scn.unit_manager
P1 = scenarios.PlayerId.ONE
um.add_unit(P1, BuildingInfo.TOWN_CENTER.ID, x=6, y=40)               # the population room
um.add_unit(P1, UnitInfo.TRANSPORT_SHIP.ID, x=15.5, y=24.5)
um.add_unit(P1, UnitInfo.MILITIA.ID, x=12.5, y=23.5)
um.add_unit(P1, UnitInfo.VILLAGER_MALE.ID, x=12.5, y=25.5)
src = f"{OUT}/ships.aoe2scenario"
scenarios.save(scn, src)
with contextlib.redirect_stdout(io.StringIO()):
    aoe2mc.convert(src, f"{OUT}/W")
data = json.load(open(f"{OUT}/W/aoe2mc.json"))
res = {}
with run.Game(f"{OUT}/W") as game, mc_shot.Client(game.game_port, game.version) as client:
    client.wait_join(lambda: "aoe2mc" in game.command("list").split(":", 1)[-1])
    game.command("gamemode adventure aoe2mc")
    game.command("attribute aoe2mc minecraft:gravity base set 0")    # the view stays where tp puts it
    game.command("clear aoe2mc")
    game.forceload()
    game.command("time set noon")
    combat.setup(game, data)
    g = gather.Gather(game, data, tick=0.25, start={}).setup()
    T = g.map.T
    ship, = [u for u, n in g.soldiers.items() if n == "TRANSPORT_SHIP"]
    mil, = [u for u, n in g.soldiers.items() if n == "MILITIA"]
    vil, = [v for v in g.villagers]
    units = [mil, vil]
    g.run(seconds=2)                                                 # the stick comes (Gather.clicks)
    client.key("1")
    time.sleep(1)
    res["hand"] = game.command("data get entity aoe2mc SelectedItem.id")

    def look_at(at, eye_off=(-10, 9, 10)):
        e = (at[0] + eye_off[0], at[1] + eye_off[1], at[2] + eye_off[2])
        # tp ... facing aims from the feet: aim 1.62 blocks lower, so that the ray of the eye goes through at
        game.command(f"tp aoe2mc {e[0]} {e[1]} {e[2]} facing {at[0]} {at[1] - 1.62} {at[2]}")
        time.sleep(1.5)

    def right_click():
        client.click(client.size[0] // 2, client.size[1] // 2, button=3)
        g.run(seconds=1.0)
        res.setdefault("clicks", []).append(game.command("scoreboard players get aoe2mc aoe_use"))

    def run_until(cond, seconds):
        t0 = time.time()
        g.run(seconds=seconds, until=cond)
        return round(time.time() - t0, 1)

    def tiles(u):
        p = g.pos(u)
        return [round(p[0] / T, 2), round(p[2] / T, 2)] if p else None

    cargo = lambda: vars(g).get("cargo", {}).get(ship, ())
    for n, (goal_tile, eye_off) in enumerate((((36.5, 24.5), (-12, 10, 8)), ((8.5, 28.5), (12, 10, 8)))):
        # load: the units are the selection (as after a box), a real right click on the ship
        g.choose(set(units), units[0])
        p = g.pos(ship)
        look_at((p[0], p[1] + 0.8, p[2]))
        right_click()
        took = run_until(lambda: len(cargo()) >= 2, 60)
        step = res.setdefault(f"trip {n + 1}", {})
        step["load"] = {"seconds": took, "inside": list(cargo())}
        # select the ship with a real right click on it, then a real right click on the land
        p = g.pos(ship)
        look_at((p[0], p[1] + 0.8, p[2]))
        g.choose(set(), None)
        right_click()
        step["selected after the click on the ship"] = sorted(g.selected)
        goal = (goal_tile[0] * T, goal_tile[1] * T)
        y = g.map.y(math.floor(goal[0]), math.floor(goal[1]))
        look_at((goal[0], y, goal[1]), eye_off)
        t0 = time.time()
        right_click()
        took = run_until(lambda: ship not in vars(g).get("cargo", {}), 150)
        step["sail seconds"] = round(time.time() - t0, 1)
        step["ship tiles at the unload"] = tiles(ship)
        step["units tiles at the unload"] = {u: tiles(u) for u in units}
        q = g.pos(ship)
        game.command(f"tp aoe2mc {q[0] + eye_off[0]} {q[1] + 12} {q[2] + eye_off[2]} facing {q[0]} {q[1]} {q[2]}")
        time.sleep(2)
        client.shot(f"{OUT}/trip{n + 1}_unload.png")
        walk = run_until(lambda: all((p := g.pos(u)) and math.dist((p[0], p[2]), goal) < 1.5 * T for u in units), 60)
        step["walk seconds"] = walk
        step["units tiles at the end"] = {u: tiles(u) for u in units}
        step["distance to the click (tiles)"] = {u: round(math.dist(tiles(u), goal_tile), 2) for u in units}
        step["goal tile"] = goal_tile
        look_at((goal[0], y, goal[1]), eye_off)
        client.shot(f"{OUT}/trip{n + 1}_end.png")
        print(json.dumps(step), flush=True)
    json.dump(res, open(f"{OUT}/res.json", "w"), indent=1, default=str)
print("done", flush=True)
