"""Check #1492 (third run: board a ship far from the shore, #1653; unload at the shore and walk, #1652. Second run: Gather.run, the play loop with the clicks, and a far land click, #1511, #1515): on Paper with the real 26.3 client. A fishing ship trained at the dock gathers a fish and brings the food
to the dock; a transport ship loads 3 militia, sails across the sea and unloads them on the other shore; two galleys of
two players fight until one sinks. The orders go through the functions of the player clicks (train.queue, fleet.fish,
transport.order, Gather.walk_to, Gather.attack)."""
import contextlib, io, json, math, sys, time
ROOT = "/home/user/aoe2mc"
sys.path[:0] = [ROOT, ROOT + "/tools", ROOT + "/game"]
import aoe2mc, scenarios, mc_shot
from AoE2ScenarioParser.datasets.buildings import BuildingInfo
from AoE2ScenarioParser.datasets.units import UnitInfo
from AoE2ScenarioParser.datasets.other import OtherInfo
import run, gather, combat, train, fleet, transport

OUT = sys.argv[1]
SHOTS = "--no-client" not in sys.argv
scn = scenarios.new_scenario(48)
for t in scn.map_manager.terrain:                                   # a sea between a west and an east shore
    if 14 <= t.x < 34:
        t.terrain_id = scenarios.TerrainId.WATER_DEEP
um = scn.unit_manager
P1, P2 = scenarios.PlayerId.ONE, scenarios.PlayerId.TWO
um.add_unit(P1, BuildingInfo.DOCK.ID, x=15.5, y=10.5)
um.add_unit(P1, BuildingInfo.TOWN_CENTER.ID, x=6, y=24)               # the population room
um.add_unit(P1, BuildingInfo.CASTLE.ID, x=6, y=4)                     # 20 more population: 6 own units
um.add_unit(scenarios.PlayerId.GAIA, OtherInfo.FISH_TUNA.ID, x=21.5, y=11.5)
um.add_unit(P1, UnitInfo.GALLEY.ID, x=20.5, y=26.5)
um.add_unit(P2, UnitInfo.GALLEY.ID, x=26.5, y=26.5)
um.add_unit(P1, UnitInfo.TRANSPORT_SHIP.ID, x=24.5, y=40.5)         # 10 tiles from each shore (#1653)
for y in (39.5, 40.5, 41.5):
    um.add_unit(P1, UnitInfo.MILITIA.ID, x=10.5, y=y)
src = f"{OUT}/ships.aoe2scenario"
scenarios.save(scn, src)
with contextlib.redirect_stdout(io.StringIO()):
    aoe2mc.convert(src, f"{OUT}/W")
data = json.load(open(f"{OUT}/W/aoe2mc.json"))
res = {}
cm = mc_shot.Client if SHOTS else None
with run.Game(f"{OUT}/W") as game, (cm(game.game_port, game.version) if SHOTS else contextlib.nullcontext()) as client:
    if SHOTS:
        client.wait_join(lambda: "aoe2mc" in game.command("list").split(":", 1)[-1])
        game.command("gamemode spectator aoe2mc")
    game.forceload()
    game.command("time set noon")
    combat.setup(game, data)
    g = gather.Gather(game, data, tick=0.25, start={}).setup()
    g.stock.update(food=1000, wood=1000, gold=1000, stone=1000)
    T = g.map.T

    def shot(name, at, look):
        if SHOTS:
            game.command(f"tp aoe2mc {at[0]} {at[1]} {at[2]} facing {look[0]} {look[1]} {look[2]}")
            time.sleep(4)
            client.shot(f"{OUT}/{name}.png")

    def run_until(cond, seconds):
        t0 = time.time()
        g.run(seconds=seconds, until=cond)                         # the play loop: point, clicks, step (#1511)
        return round(time.time() - t0, 1)

    # 1. the fishing ship
    homes = train.homes(g)
    print("homes", homes, "docks", g.map.docks, "fish", g.map.fish, flush=True)
    rect, = [r for r, n in homes.items() if n == "DOCK"]
    before = dict(g.stock)
    ok = train.queue(g, "nobody", rect[::2], "FISHING_SHIP")
    cost = {k: before[k] - g.stock[k] for k in before if before[k] != g.stock[k]}
    new = train.tick(g, train.TRAIN_TIMES["FISHING_SHIP"])
    boat = new[0] if new else None
    res["train fishing ship"] = {"queued": bool(ok), "cost": cost, "time": train.TRAIN_TIMES["FISHING_SHIP"], "uuid": boat,
                                 "pos": g.pos(boat) if boat else None}
    print(res["train fishing ship"], flush=True)
    tile = (21, 11)
    fish0, food0 = g.map.fish.get(tile), g.stock["food"]
    sent = fleet.fish(g, {boat}, tile) if boat else set()
    trace = []

    def fished():
        v = g.ships.get(boat)
        if v and (not trace or trace[-1][0] != v.state):
            trace.append((v.state, round(time.time() - t_f, 1), [round(c, 1) for c in g.pos(boat)]))
            if v.state == "chop" and not any(s[0] == "chop" for s in trace[:-1]):
                p = g.pos(boat)
                shot("fishing", (p[0] - 6, p[1] + 5, p[2] + 6), p)
        return g.stock["food"] > food0
    t_f = time.time()
    assert boat, "no fishing ship"
    took = run_until(fished, 240)
    res["fishing"] = {"sent": bool(sent), "fish before": fish0, "fish after": g.map.fish.get(tile), "food before": food0,
                      "food after": g.stock["food"], "seconds": took, "states": trace,
                      "scoreboard": game.command(f"scoreboard players get Food {g.board}")}
    print("fishing", res["fishing"], flush=True)
    d = rect
    shot("fishing_drop", (d[1] + 6, 78, d[3] + 10), ((d[0] + d[1]) / 2, 66, (d[2] + d[3]) / 2))

    # 2. the transport ship
    ship, = [u for u, n in g.soldiers.items() if n == "TRANSPORT_SHIP"]
    mil = sorted(u for u, n in g.soldiers.items() if n == "MILITIA")
    ship0 = g.pos(ship)
    g.choose(set(mil), mil[0])
    ok = transport.order(g, "nobody", ship)
    took = run_until(lambda: len(vars(g).get("cargo", {}).get(ship, ())) >= 3, 90)
    res["ship before and after the load"] = [ship0, g.pos(ship)]
    inside = game.command(f"execute as {ship} on passengers run data get entity @s Passengers")
    res["transport load"] = {"order": bool(ok), "seconds": took, "inside": vars(g).get("cargo", {}).get(ship), "riders": inside[:300]}
    print("load", res["transport load"], flush=True)
    p = g.pos(ship)
    shot("transport_loaded", (p[0] - 8, p[1] + 6, p[2] + 6), p)
    goal = (35 * T + 1, 40 * T + 1)                                  # one tile inland (fleet.NEAR)
    g.choose({ship}, ship)
    sailed = g.walk_to("nobody", goal)
    took = run_until(lambda: ship not in vars(g).get("cargo", {}), 150)
    out = {m: [round(c / T, 2) for c in g.pos(m)] for m in mil}                # tiles, just after the unload
    shipat = [round(c / T, 2) for c in g.pos(ship)]
    walk = run_until(lambda: all((p := g.pos(m)) and math.dist((p[0], p[2]), goal) < 1.5 * T for m in mil), 30)
    after = {m: g.pos(m) for m in mil}
    res["transport unload"] = {"sailing": ship in sailed, "seconds": took, "goal": goal, "out tiles": out,
                               "ship tiles": shipat, "walk seconds": walk,
                               "militia": {m: [round(c, 1) for c in p] if p else None for m, p in after.items()},
                               "dist tiles": {m: round(math.dist((p[0], p[2]), goal) / T, 2) if p else None for m, p in after.items()},
                               "on land": {m: bool(p) and g.map.free(math.floor(p[0]), math.floor(p[2])) for m, p in after.items()},
                               "ship": g.pos(ship)}
    print("unload", res["transport unload"], flush=True)
    shot("transport_unloaded", (goal[0] - 10, 76, goal[1] + 8), (goal[0], 66, goal[1]))

    # 2b. load again and send the ship 10 tiles inland on the west shore (#1515)
    g.choose(set(mil), mil[0])
    ok = transport.order(g, "nobody", ship)
    took = run_until(lambda: len(vars(g).get("cargo", {}).get(ship, ())) >= 3, 90)
    res["transport load 2"] = {"order": bool(ok), "seconds": took, "inside": vars(g).get("cargo", {}).get(ship)}
    print("load 2", res["transport load 2"], flush=True)
    far = (4 * T + 1, 40 * T + 1)                                    # 10 tiles from the water (x 14)
    g.choose({ship}, ship)
    sailed = g.walk_to("nobody", far)
    took = run_until(lambda: ship not in vars(g).get("cargo", {}), 150)
    shore = {m: g.pos(m) for m in mil}
    walk = run_until(lambda: all((p := g.pos(m)) and math.dist((p[0], p[2]), far) < 3 * T for m in mil), 60)
    after = {m: g.pos(m) for m in mil}
    res["transport far"] = {"sailing": ship in sailed, "goal": far, "sail seconds": took, "walk seconds": walk,
                            "shore x tiles": {m: round(p[0] / T, 1) if p else None for m, p in shore.items()},
                            "dist tiles": {m: round(math.dist((p[0], p[2]), far) / T, 2) if p else None for m, p in after.items()},
                            "ship": g.pos(ship)}
    print("far", res["transport far"], flush=True)
    shot("transport_far", (far[0] + 12, 78, far[1] + 10), (far[0], 66, far[1]))

    # 3. two galleys fight
    gal = sorted(u for u, n in g.soldiers.items() if n == "GALLEY")
    print("galleys", gal, "enemies", g.enemies, flush=True)
    own = gal[0]
    enemy = next((u for u, n in sorted(g.enemies.items()) if n == "GALLEY"), None)

    def crew_hp(u):
        out = game.command(f"execute as {u} on passengers run data get entity @s Health")
        try:
            return float(out.rsplit(":", 1)[-1].strip().rstrip("f"))
        except ValueError:
            return None
    alive = lambda u: "Test passed" in game.command(f"execute if entity {u}")
    g.choose({own}, own)
    g.attack(enemy)
    log, t_g, shotted = [], time.time(), False

    def fought():
        global shotted
        log.append((round(time.time() - t_g, 1), crew_hp(own), crew_hp(enemy)))
        if not shotted and log[-1][2] is not None and log[-1][2] < log[0][2]:
            shotted = True
            a, b = g.pos(own), g.pos(enemy)
            if a and b:
                shot("galley_fight", ((a[0] + b[0]) / 2, a[1] + 8, a[2] + 14), ((a[0] + b[0]) / 2, a[1], a[2]))
        return not alive(enemy) or not alive(own)
    took = run_until(fought, 150)
    res["galleys"] = {"own": own, "enemy": enemy, "seconds": took, "own alive": alive(own), "enemy alive": alive(enemy),
                      "log": log[::4] + log[-2:], "AoE2": combat.damage("GALLEY", "GALLEY")}
    print("galleys", {k: v for k, v in res["galleys"].items() if k != "log"}, log[-3:], flush=True)
    a = g.pos(own) or (26 * T, 64, 26 * T)
    shot("galley_after", (a[0] + 4, a[1] + 8, a[2] + 14), a)
    json.dump(res, open(f"{OUT}/res.json", "w"), indent=1, default=str)
print("done", flush=True)
