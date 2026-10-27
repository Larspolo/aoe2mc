"""Check #1204: the arrows of the town center, a watch tower and a castle on Paper, with 0 and 3 villagers inside."""
import contextlib, io, json, os, sys, time
ROOT = "/home/user/aoe2mc"
sys.path[:0] = [ROOT, ROOT + "/tools", ROOT + "/game"]
import aoe2mc, scenarios, mc_shot
from AoE2ScenarioParser.datasets.buildings import BuildingInfo
from AoE2ScenarioParser.datasets.units import UnitInfo
import run, gather, garrison, combat

OUT = sys.argv[1]
scn = scenarios.new_scenario(48)
um = scn.unit_manager
B = {"TOWN_CENTER": (10, 10), "WATCH_TOWER": (24, 10), "CASTLE": (38, 10)}
for n, (x, y) in B.items():
    um.add_unit(scenarios.PlayerId.ONE, getattr(BuildingInfo, n).ID, x=x, y=y)
    um.add_unit(scenarios.PlayerId.TWO, UnitInfo.MILITIA.ID, x=x + 0.5, y=y + 5.5)
for i in range(3):
    um.add_unit(scenarios.PlayerId.ONE, UnitInfo.VILLAGER_MALE.ID, x=17.5 + i, y=16.5)
src = f"{OUT}/arrows.aoe2scenario"
scenarios.save(scn, src)
with contextlib.redirect_stdout(io.StringIO()):
    aoe2mc.convert(src, f"{OUT}/W")
data = json.load(open(f"{OUT}/W/aoe2mc.json"))
rects = {o["name"]: o["footprint"] for o in data["objects"] if o["kind"] == "building"}
print("footprints", rects)


def hp(game, u):
    out = game.command(f"data get entity {u} Health")
    try:
        return float(out.rsplit(":", 1)[-1].strip().rstrip("f"))
    except ValueError:
        return None


with run.Game(f"{OUT}/W") as game, mc_shot.Client(game.game_port, game.version) as client:
    client.wait_join(lambda: "aoe2mc" in game.command("list").split(":", 1)[-1])
    game.forceload()
    game.command("gamemode spectator aoe2mc")
    game.command("time set noon")
    g = gather.Gather(game, data).setup()
    combat.setup(game, data)
    foes = sorted(g.enemies)
    pos = g.positions(foes)
    near = {}
    for n, (x0, z0, x1, z1) in rects.items():
        c = ((x0 + x1) / 2, (z0 + z1) / 2)
        near[n] = min(foes, key=lambda u: (pos[u][0] - c[0]) ** 2 + (pos[u][2] - c[1]) ** 2)
    print("enemies", near, {u: pos[u] for u in foes})
    for u in foes:
        game.command(f"data merge entity {u} {{NoAI:1b}}")
        game.command(f"attribute {u} minecraft:max_health base set 1000")
        game.command(f"data modify entity {u} Health set value 1000f")

    home = {u: pos[u] for u in foes}

    def heal(skip=None):
        for m in near:
            if m != skip:
                game.command(f"data modify entity {near[m]} Health set value 1000f")
        for u in foes:                                              # each building keeps its own enemy (#1328 note)
            game.command(f"data merge entity {u} {{NoAI:1b}}")
            game.command(f"tp {u} {home[u][0]} {home[u][1]} {home[u][2]}")

    def shots(n, name):
        x0, z0, x1, z1 = rects[n]
        bx, bz = (x0 + x1) / 2, (z0 + z1) / 2
        ex, ey, ez = home[near[n]]
        game.command(f"tp aoe2mc {ex + 7} {ey + 3} {ez + 5} facing {bx} {ey + 6} {bz}")
        time.sleep(5)
        for k in range(4):
            g.step(); heal(); time.sleep(0.2)
            client.shot(f"{OUT}/{name}_{k}.png")

    def damage(n, seconds=8.0, keep=None):
        keep = keep or (lambda: heal(n))
        u = near[n]
        game.command(f"data modify entity {u} Health set value 1000f")
        h0, t0 = hp(game, u), time.time()
        hits = []
        last = h0
        while time.time() - t0 < seconds:
            g.step()
            keep()
            h = hp(game, u)
            if h is not None and last is not None and h < last:
                hits.append(round(last - h, 2))
            last = h
            time.sleep(g.tick)
        return round(h0 - (last or 0), 1), hits

    res = {}
    for n in B:
        res[(n, 0)] = damage(n)
        print(n, 0, res[(n, 0)], flush=True)
    vill = sorted(g.villagers)

    def garrison_into(n):
        x0, z0, x1, z1 = rects[n]
        g.choose(set(vill), vill[0])
        assert garrison.order(g, "aoe2mc", (x0 + 1, z0 + 1)), n
        t0 = time.time()
        rect = (x0, x1, z0, z1)
        while len(g.garrisons.get(rect, [])) < 3 and time.time() - t0 < 60:
            g.step()
            heal()
            time.sleep(g.tick)
        print("inside", n, len(g.garrisons.get(rect, [])), time.time() - t0, g.entering, g.positions(vill), garrison.door(g, rect), flush=True)
        return rect

    r = garrison_into("WATCH_TOWER")
    res[("WATCH_TOWER", 3)] = damage("WATCH_TOWER")
    print("WATCH_TOWER", 3, res[("WATCH_TOWER", 3)], flush=True)
    shots("WATCH_TOWER", "tower")
    garrison.out(g, r)
    for _ in range(10):
        g.step(); heal(); time.sleep(g.tick)
    r = garrison_into("TOWN_CENTER")
    res[("TOWN_CENTER", 3)] = damage("TOWN_CENTER")
    print("TOWN_CENTER", 3, res[("TOWN_CENTER", 3)], flush=True)
    shots("TOWN_CENTER", "tc")
    garrison.out(g, r)
    for _ in range(10):
        g.step(); heal(); time.sleep(g.tick)
    r = garrison_into("WATCH_TOWER")                                  # the note: tower after the town center
    res[("WATCH_TOWER", "3 again")] = damage("WATCH_TOWER")
    print("WATCH_TOWER 3 again", res[("WATCH_TOWER", "3 again")], flush=True)
    print(game.command(garrison.arrows_command(g, r)))
    print('villagers alive', len(g.villagers), flush=True)
    garrison.out(g, r)
    for _ in range(10):
        g.step(); heal(); time.sleep(g.tick)
    r = garrison_into("CASTLE")
    res[("CASTLE", 3)] = damage("CASTLE")
    print("CASTLE", 3, res[("CASTLE", 3)], flush=True)
    shots("CASTLE", "castle")
    json.dump({f"{k[0]} {k[1]}": v for k, v in res.items()}, open(f"{OUT}/res.json", "w"), indent=1)
print("done")
