"""Check #3519 on Paper with a real client: waypoints, attack queue, build queue."""
import json, math, os, shutil, subprocess, sys, time
sys.path[:0] = ["tools", "."]
import mc_shot, scenarios
from AoE2ScenarioParser.datasets.players import PlayerId
from AoE2ScenarioParser.datasets.units import UnitInfo
from AoE2ScenarioParser.datasets.buildings import BuildingInfo
from game import run, gather, build

OUT = sys.argv[1]
scn = scenarios.new_scenario(32)
um = scn.unit_manager
um.add_unit(PlayerId.ONE, BuildingInfo.TOWN_CENTER.ID, x=6, y=6)
for i in range(3):
    um.add_unit(PlayerId.ONE, UnitInfo.MILITIA.ID, x=12.5 + i, y=12.5)
for i in range(2):
    um.add_unit(PlayerId.ONE, UnitInfo.VILLAGER_MALE.ID, x=6.5 + i, y=12.5)
for i in range(2):
    um.add_unit(PlayerId.TWO, UnitInfo.MILITIA.ID, x=24.5, y=20.5 + 3 * i)
scenarios.save(scn, f"{OUT}/t.aoe2scenario")
shutil.rmtree(f"{OUT}/W", ignore_errors=True)
subprocess.run([sys.executable, "aoe2mc.py", f"{OUT}/t.aoe2scenario", f"{OUT}/W"], check=True, stdout=subprocess.DEVNULL)
data = json.load(open(f"{OUT}/W/aoe2mc.json"))
log = open(f"{OUT}/log.txt", "w")
def say(*a):
    print(*a, flush=True); print(*a, file=log, flush=True)

with run.Game(f"{OUT}/W") as game, mc_shot.Client(game.game_port, game.version) as client:
    client.wait_join(lambda: "aoe2mc" in game.command("list").split(":", 1)[-1])
    time.sleep(5)
    game.forceload()
    g = gather.Gather(game, data).setup()
    g.stock.update(wood=500, food=500, gold=500, stone=500)
    game.command("item replace entity aoe2mc hotbar.0 with minecraft:carrot_on_a_stick")
    game.command("gamemode survival aoe2mc"); game.command("effect give aoe2mc minecraft:resistance infinite 4 true")
    client.key("1")
    mine = [u for u, k in g.soldiers.items() if g.owner(u) == 1] if hasattr(g, "owner") else None
    say("soldiers", g.soldiers, "villagers", list(g.villagers))
    def ground(x, z, sneak):
        y = g.map.y(x, z) or 64
        g.command(f"tp aoe2mc {x + 0.5:.2f} {y + 4:.2f} {z + 4.5:.2f} facing {x + 0.5:.2f} {y + 0.5:.2f} {z + 0.5:.2f}")
        time.sleep(1.0)
        if sneak:
            client.xdo("keydown", "Shift_L"); time.sleep(0.5)
        client.click(640, 360, button=3)
        g.run(seconds=1.0)
        if sneak:
            client.xdo("keyup", "Shift_L")
        say("after click", (x, z), sneak, where(g.selected))
    def camera(x, z, name, us=None):
        if us and (p := g.positions(sorted(us))):
            x, z = (round(sum(v[0] for v in p.values()) / len(p)), round(sum(v[2] for v in p.values()) / len(p)))
        g.command("gamemode spectator aoe2mc")                         # no fall: creative without flight falls
        g.command(f"tp aoe2mc {x} 92 {z + 20} facing {x} 64 {z}")
        g.run(seconds=1.5)
        say("camera", name, g.pos("aoe2mc"))
        client.shot(f"{OUT}/{name}.png")
        g.command("gamemode survival aoe2mc")                          # creative after spectator flies: Shift descends, no sneak
    def where(us):
        p = g.positions(sorted(us))
        return {u[:6]: (round(v[0]), round(v[2])) for u, v in p.items()}

    sold, foes = list(g.soldiers), list(g.enemies)
    say("own", g.soldiers, "enemies", g.enemies, "villagers", list(g.villagers))
    # 1. waypoints: a normal click, then two sneak clicks
    P = [(40, 96), (96, 96), (96, 40)]
    g.choose(set(sold), sold[0])
    camera(60, 60, "w0_start")
    ground(*P[0], False); ground(*P[1], True); ground(*P[2], True)
    say("queue", g.waypoints)
    t0, seen, shots = time.time(), [], 1
    while time.time() - t0 < 120:
        g.run(seconds=1.0)
        pos = g.positions(sorted(sold))
        for i, p in enumerate(P):
            if i not in seen and any(math.dist((v[0], v[2]), (p[0] + .5, p[1] + .5)) <= 4 for v in pos.values()):
                seen.append(i); say(f"{time.time() - t0:.0f} s at point {i + 1}", where(sold))
                camera(p[0], p[1], f"w{i + 1}_point{i + 1}", sold)
        if len(seen) == 3 and not g.waypoints:
            break
    say("waypoint order", [i + 1 for i in seen], "queue left", g.waypoints)
    # 3. build queue: a normal click on site A, a sneak click on site B
    A = build.found(g, "HOUSE", (40, 48, 60, 68)); B = build.found(g, "HOUSE", (64, 72, 60, 68))
    vill = list(g.villagers)
    g.choose(set(vill), vill[0])
    g.run(seconds=3)
    ground(44, 64, False); ground(68, 64, True)
    say("sites", [g.villagers[v].site is A for v in vill], "queue", {v[:6]: [q is B for q in x] if isinstance(x, list) else x for v, x in vars(g).get("site_queue", {}).items()})
    camera(56, 64, "b0_start")
    t0, done = time.time(), {}
    while time.time() - t0 < 180 and len(done) < 2:
        g.run(seconds=1.0)
        for n, s in (("A", A), ("B", B)):
            if s["progress"] >= 1 and n not in done:
                done[n] = round(time.time() - t0); say("site", n, "done", done[n], "s")
                camera(56, 64, f"b{len(done)}_{n}_done")
        if int(time.time() - t0) == 5: camera(56, 64, "b0b_at_A", vill)
    say("build order", done, "A", A["progress"], "B", B["progress"])
    # 2. attack queue: sneak clicks on 2 enemies
    for c in ("effect give @e[type=!player] minecraft:slowness 1 0",):
        pass
    for u in foes:
        game.command(f"data merge entity {u} {{NoAI:1b}}")
    g.choose(set(sold), sold[0])
    picks = []
    for u in foes:
        feet = g.pos(u); mid = (feet[0], feet[1] + 1.0, feet[2]); hit = None
        for stand, face in [((mid[0] + d * dx, feet[1], mid[2] + d * dz), (mid[0], mid[1] - 1.62 + (feet[1] - (mid[1] - 1.62)) * 0, mid[2])) for d in (3, 4, 5) for dx, dz in ((0, 1), (0, -1), (1, 0), (-1, 0))]:
            g.command(f"tp aoe2mc {stand[0]:.2f} {stand[1]:.2f} {stand[2]:.2f} facing {face[0]:.2f} {face[1]:.2f} {face[2]:.2f}")
            time.sleep(0.5)
            if (look := g.look("aoe2mc")) and mc_shot.hits(g.target(*look, g.positions(sorted(g.pickable()))), u):
                hit = stand; break
        client.xdo("keydown", "Shift_L"); time.sleep(0.5)                # after the tp: a tp can end the sneak
        say("sneak", game.command(f"execute as aoe2mc if predicate {gather.SNEAK}"))
        client.click(640, 360, button=3)
        picks.append(hit)
        g.run(seconds=1.0)
        client.xdo("keyup", "Shift_L")
        say("after pick", u[:6], {k[:6]: v for k, v in vars(g).get("waypoints", {}).items()},
            {k[:6]: (v if not isinstance(v, dict) else {"attack": v["attack"][:6]}) for k, v in vars(g).get("waypoint_at", {}).items()})
    say("picked", picks, "queue", g.waypoints)
    camera(*[round(v) for v in (g.pos(foes[0])[0], g.pos(foes[0])[2])], "a0_start")
    t0, dead = time.time(), {}
    while time.time() - t0 < 90 and len(dead) < 2:
        g.run(seconds=1.0)
        alive = g.positions(foes)
        for u in foes:
            if u not in alive and u not in dead:
                dead[u] = round(time.time() - t0); say("dead", u[:6], dead[u], "s")
                if len(dead) == 1 and (rest := [f for f in foes if f in alive]):
                    p = alive[rest[0]]; camera(round(p[0]), round(p[2]), "a1_first_dead", sold)
    say("attack order", [foes.index(u) + 1 for u in dead], dead)
