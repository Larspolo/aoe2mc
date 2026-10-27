"""Check #1353: train a ram, a mangonel and a scorpion at the siege workshop and a trebuchet at the castle on Paper;
a ram against an enemy barracks, a mangonel against 5 enemy militia, a scorpion bolt, a trebuchet that unpacks, shoots a
building and packs. Damage next to combat.damage (the AoE2 rule). Real 26.3 client for the images."""
import contextlib, io, json, math, sys, time
ROOT = "/tmp/claude-0/-home-user-aoe2mc/95e169a0-503b-5bf5-b261-8bb7b51a400c/scratchpad/main"
sys.path[:0] = [ROOT, ROOT + "/tools", ROOT + "/game"]
import aoe2mc, scenarios, mc_shot
from AoE2ScenarioParser.datasets.buildings import BuildingInfo
from AoE2ScenarioParser.datasets.units import UnitInfo
import run, gather, combat, train, ai, trebuchet

OUT = sys.argv[1]
SHOTS = "--no-client" not in sys.argv
scn = scenarios.new_scenario(48)
um = scn.unit_manager
P1, P2 = scenarios.PlayerId.ONE, scenarios.PlayerId.TWO
um.add_unit(P1, BuildingInfo.SIEGE_WORKSHOP.ID, x=8, y=8)
um.add_unit(P1, BuildingInfo.CASTLE.ID, x=8, y=36)
um.add_unit(P2, BuildingInfo.BARRACKS.ID, x=22, y=8)          # the ram target
um.add_unit(P2, BuildingInfo.BLACKSMITH.ID, x=30, y=40)       # the trebuchet target
MIL = [(23.0, 21.0), (22.4, 21.0), (23.6, 21.0), (23.0, 20.4), (23.0, 21.6)]   # the mangonel group
SCO = [(8.0, 22.0), (8.0, 23.0), (8.0, 24.0)]                            # the scorpion targets
for x, y in MIL + SCO:
    um.add_unit(P2, UnitInfo.MILITIA.ID, x=x, y=y)
src = f"{OUT}/siege.aoe2scenario"
scenarios.save(scn, src)
with contextlib.redirect_stdout(io.StringIO()):
    aoe2mc.convert(src, f"{OUT}/W")
data = json.load(open(f"{OUT}/W/aoe2mc.json"))
rects = {o["name"]: o["footprint"] for o in data["objects"] if o["kind"] == "building"}
print("footprints", rects, flush=True)
res = {}


def hp(game, u):
    out = game.command(f"data get entity {u} Health")
    try:
        return float(out.rsplit(":", 1)[-1].strip().rstrip("f"))
    except ValueError:
        return None


def fort_hp(game, f):
    out = game.command(f"scoreboard players get {f} aoe_hp")
    return int(out.split(" has ")[1].split()[0]) if " has " in out else None


cm = mc_shot.Client if SHOTS else None
with run.Game(f"{OUT}/W") as game, (cm(game.game_port, game.version) if SHOTS else contextlib.nullcontext()) as client:
    if SHOTS:
        client.wait_join(lambda: "aoe2mc" in game.command("list").split(":", 1)[-1])
        game.command("gamemode spectator aoe2mc")
    game.forceload()
    game.command("time set noon")
    combat.setup(game, data)
    g = gather.Gather(game, data, tick=0.25, start={}).setup()
    g.techs.update(train.build.AGE_TECHS)                           # the Imperial Age (the trebuchet)
    g.stock.update(food=2000, wood=2000, gold=2000, stone=2000)
    foes = sorted(g.enemies)
    pos = g.positions(foes)
    for u in foes:
        game.command(f"data merge entity {u} {{NoAI:1b}}")
        game.command(f"attribute {u} minecraft:max_health base set 1000")
        game.command(f"data modify entity {u} Health set value 1000f")
    home = dict(pos)
    T = g.map.T

    def keep():
        for u in foes:
            game.command(f"data merge entity {u} {{NoAI:1b}}")

    def near(c, k):
        return sorted(foes, key=lambda u: (pos[u][0] - c[0]) ** 2 + (pos[u][2] - c[1]) ** 2)[:k]

    def shot(name, at, look):
        if not SHOTS:
            return
        game.command(f"tp aoe2mc {at[0]} {at[1]} {at[2]} facing {look[0]} {look[1]} {look[2]}")
        time.sleep(4)
        client.shot(f"{OUT}/{name}.png")

    homes = train.homes(g)
    print("homes", homes, flush=True)
    made = {}
    for b, name in [("SIEGE_WORKSHOP", "SCORPION")]:
        rect, = [r for r, n in homes.items() if n == b]
        before = dict(g.stock)
        ok = train.queue(g, "nobody", rect[::2], name)
        cost = {k: before[k] - g.stock[k] for k in before if before[k] != g.stock[k]}
        new = train.tick(g, train.TRAIN_TIMES[name])
        made[name] = new[0] if new else None
        res[f"train {name}"] = {"queued": bool(ok), "cost": cost, "time": train.TRAIN_TIMES[name], "uuid": made[name],
                               "pos": g.pos(made[name]) if made[name] else None}
        print("train", name, res[f"train {name}"], flush=True)
    for _ in range(8):
        g.step(); keep(); time.sleep(g.tick)
    ws = rects["SIEGE_WORKSHOP"]
    shot("trained", (ws[2] + 10, 80, ws[3] + 10), ((ws[0] + ws[2]) / 2, 66, (ws[1] + ws[3]) / 2))

    def fight(name, target, seconds, units=(), fort=None):
        u = made[name]
        g.choose({u}, u)
        g.attack(target)
        watch = list(units)
        h = {w: hp(game, w) for w in watch}
        f0 = fort_hp(game, fort) if fort else None
        hits, fh, t0, first = {w: [] for w in watch}, [], time.time(), None
        while time.time() - t0 < seconds:
            g.step(); keep()
            for w in watch:
                v = hp(game, w)
                if v is not None and h[w] is not None and v < h[w]:
                    hits[w].append(round(h[w] - v, 2))
                    first = first or round(time.time() - t0, 1)
                h[w] = v
            if fort:
                v = fort_hp(game, fort)
                if v is not None and f0 is not None and v < f0:
                    fh.append(f0 - v)
                    first = first or round(time.time() - t0, 1)
                f0 = v if v is not None else f0
            time.sleep(g.tick)
        return {"hits": hits, "fort hits": fh, "first hit s": first, "end": g.pos(u)}

    sco = near((8 * T, 22 * T), 1) + near((8 * T, 23 * T), 1) + near((8 * T, 24 * T), 1)
    res["scorpion vs militia"] = fight("SCORPION", sco[0], 30, units=sco)
    res["scorpion vs militia"]["AoE2"] = combat.damage("SCORPION", "MILITIA")
    print("scorpion", res["scorpion vs militia"], flush=True)
    c = pos[sco[0]]
    shot("scorpion_line", (c[0] - 10, c[1] + 5, c[2] + 8), (c[0], c[1], c[2] + 4))
    res["scorpion vs militia"]["targets"] = {u: pos[u] for u in sco}

    json.dump(res, open(f"{OUT}/res.json", "w"), indent=1, default=str)
print("done", flush=True)
