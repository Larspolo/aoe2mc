"""Why does a bot militia die at about 1:40 on owner_loop before any attack? Usage: OUTDIR"""
import contextlib, io, json, os, shutil, sys, time
ROOT = "/home/user/aoe2mc"
sys.path[:0] = [ROOT, os.path.join(ROOT, "game"), os.path.join(ROOT, "tools")]
import aoe2mc, scenarios, run, gather, combat, bot  # noqa
out = sys.argv[1]
src, world = os.path.join(out, "loop.aoe2scenario"), os.path.join(out, "W")
scenarios.owner_loop(src)
shutil.rmtree(world, ignore_errors=True)
with contextlib.redirect_stdout(io.StringIO()):
    aoe2mc.convert(src, world)
data = json.load(open(os.path.join(world, "aoe2mc.json")))
with run.Game(world) as game:
    game.forceload()
    end = time.time() + 60
    while True:
        me = gather.Gather(game, data).setup()
        b = bot.Bot(game, data, share=me, attack=180.0).setup()
        if me.villagers and b.g.villagers:
            break
        time.sleep(1)
    me.bots = [b]
    combat.setup(game, data)
    last, seen = -1, set()
    while b.time < 95:
        me.run(1)
        if int(b.time) == last:
            continue
        last = int(b.time)
        hp = {u[:8]: game.command(f"data get entity {u} Health").split(":")[-1].strip() for u in sorted(b.g.soldiers)}
        hp |= {"p" + u[:8]: game.command(f"data get entity {u} Pos").split(":", 1)[-1].strip() for u in sorted(b.g.soldiers)[:1]}
        print(round(b.time, 1), json.dumps(hp), flush=True)
        if last // 12 in (5, 6, 7) and last // 12 not in seen:
            seen.add(last // 12)
            u = [k for k in b.g.soldiers if k.startswith("3b838387")][0]
            for p in ("Fire", "Air", "HurtTime", "Pos"):
                print(p, game.command(f"data get entity {u} {p}").split(":", 1)[-1])
            for dy in (0, 1, 2):
                print("block y+%d" % dy, [k for k in ("air", "barrier", "scaffolding", "oak_planks", "oak_fence", "stone", "dirt", "grass_block", "oak_log", "cobblestone") if "passed" in game.command(f"execute at {u} if block ~ ~{dy} ~ minecraft:{k}")])
            print("sites", [(s["name"], s.get("footprint")) for s in b.g.sites])
    print("log:", game.world if hasattr(game, "world") else "")
    print(open(os.path.join(os.path.dirname(game.world), "logs", "latest.log")).read()[-6000:] if os.path.exists(os.path.join(os.path.dirname(game.world), "logs", "latest.log")) else "no log")
