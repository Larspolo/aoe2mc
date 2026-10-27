"""Check of #1691 and #964: the bot of player 2 attacks on the owner_loop map (a lake with a dock, a transport ship and
3 militia of player 1 at its north shore), as `game/run.py --play --bot --bot-attack 3:00`, with a real client.
Each game second: the feet position of each bot soldier and the blocks at its feet and below. Usage: OUTDIR"""
import contextlib, io, json, math, os, shutil, sys, time
ROOT = "/home/user/aoe2mc"
sys.path[:0] = [ROOT, os.path.join(ROOT, "game"), os.path.join(ROOT, "tools")]
import aoe2mc, scenarios, run, gather, combat, bot, mc_shot  # noqa

out = sys.argv[1]
src, world = os.path.join(out, "loop.aoe2scenario"), os.path.join(out, "W")
scenarios.owner_loop(src)
shutil.rmtree(world, ignore_errors=True)
with contextlib.redirect_stdout(io.StringIO()):
    aoe2mc.convert(src, world)
data = json.load(open(os.path.join(world, "aoe2mc.json")))
ATTACK, END = 180.0, float(sys.argv[2]) if len(sys.argv) > 2 else 720.0
log = open(os.path.join(out, "track.jsonl"), "w")


def water(game, x, y, z):
    return "passed" in game.command(f"execute if block {x} {y} {z} minecraft:water")


with run.Game(world) as game:
    game.forceload()
    end = time.time() + 60
    while True:
        me = gather.Gather(game, data).setup()
        b = bot.Bot(game, data, share=me, attack=ATTACK).setup()
        if me.villagers and b.g.villagers:
            break
        assert time.time() < end, "the villagers did not load"
        time.sleep(1)
    me.bots = [b]
    combat.setup(game, data)
    T = me.map.T
    p1 = sorted(me.villagers.keys() | me.soldiers.keys())
    print("p1 units", len(p1), "p1 soldiers", sorted(me.soldiers.values()), "bot soldiers", sorted(b.g.soldiers.values()), flush=True)
    worst, wet_cells, drowned_max, hits = 0, 0, 0, {}
    with mc_shot.Client(game.game_port, game.version) as c:
        c.wait_join(lambda: "aoe2mc" in game.command("list"))
        game.command("gamemode spectator aoe2mc")
        shots, last = {}, -1
        while b.time < END:
            me.run(1)
            sec = int(b.time)
            if sec == last:
                continue
            last = sec
            pos = b.g.positions(sorted(b.g.soldiers))
            row = dict(t=round(b.time, 1), alive=len(pos), targets=len(b.targets),
                       p1=len(me.positions(p1)), units={})
            for u, (x, y, z) in pos.items():
                bx, by, bz = math.floor(x), math.floor(y + 0.01), math.floor(z)
                feet, below, head = water(game, bx, by, bz), water(game, bx, by - 1, bz), water(game, bx, by + 1, bz)
                cell = me.map.y(bx, bz) is None                        # a water cell of the map
                depth = feet + below
                worst = max(worst, depth + head)
                wet_cells += cell
                row["units"][u[:8]] = [round(x, 1), round(y, 1), round(z, 1), int(feet), int(below), int(head), int(cell),
                                       b.targets.get(u, "")[:8]]
                hits.setdefault(b.targets.get(u, "")[:8], 0)
            dr = game.command("execute if entity @e[type=drowned]")
            n = int(dr.split()[-1]) if "passed" in dr and dr.split()[-1].isdigit() else 0
            drowned_max = max(drowned_max, n)
            row["drowned"] = n
            if sec % 10 == 0:
                forts = b.forts()
                row["forts"] = len(forts)
                row["on_buildings"] = sum(t in forts for t in b.targets.values())
                hits["forts_min"] = min(hits.get("forts_min", 99), len(forts))
                hits["on_buildings_max"] = max(hits.get("on_buildings_max", 0), row["on_buildings"])
            log.write(json.dumps(row) + "\n"); log.flush()
            if sec % 30 == 0:
                print(json.dumps({k: row.get(k) for k in ("t", "alive", "targets", "p1", "drowned", "forts", "on_buildings")}),
                      "max feet+below+head water", worst, flush=True)
            if sec in (540, 600, 660, 720, 780, 840, 900) and pos:
                xs = [p[0] for p in pos.values()]; zs = [p[2] for p in pos.values()]; ys = [p[1] for p in pos.values()]
                x, y, z = sum(xs) / len(xs), max(ys), sum(zs) / len(zs)
                game.command(f"tp aoe2mc {x + 10:.1f} {y + 9:.1f} {z - 10:.1f} 45 35")
                time.sleep(5)
                c.shot(os.path.join(out, f"t{sec}.png"))
        print("forts", hits.get("forts_min"), "on_buildings max", hits.get("on_buildings_max"))
        print("end", b.time, "worst", worst, "wet cells", wet_cells, "drowned max", drowned_max)
        print("p1 alive", len(me.positions(p1)), "of", len(p1))
        print("p1 alive list", sorted(me.soldiers[u] if u in me.soldiers else "VILLAGER" for u in me.positions(p1)))
