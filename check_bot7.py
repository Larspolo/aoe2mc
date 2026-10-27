"""Check of #964 (seventh): the bot of player 2 on the owner_loop map, as `game/run.py --play --bot --bot-attack 3:00`,
with a real client. Each game second: the stock, units, buildings and sites of the bot, its targets, and the units and
buildings of player 1. Usage: OUTDIR [END_SECONDS]"""
import contextlib, io, json, os, shutil, sys, time
ROOT = "/home/user/aoe2mc"
sys.path[:0] = [ROOT, os.path.join(ROOT, "game"), os.path.join(ROOT, "tools")]
import aoe2mc, scenarios, run, gather, combat, bot, train, mc_shot  # noqa

out = sys.argv[1]
src, world = os.path.join(out, "loop.aoe2scenario"), os.path.join(out, "W")
scenarios.owner_loop(src)
shutil.rmtree(world, ignore_errors=True)
with contextlib.redirect_stdout(io.StringIO()):
    aoe2mc.convert(src, world)
data = json.load(open(os.path.join(world, "aoe2mc.json")))
ATTACK, END = 180.0, float(sys.argv[2]) if len(sys.argv) > 2 else 840.0
log = open(os.path.join(out, "track.jsonl"), "w")

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
    p1 = sorted(me.villagers.keys() | me.soldiers.keys())
    first, boxes, done = None, None, set()
    with mc_shot.Client(game.game_port, game.version) as c:
        c.wait_join(lambda: "aoe2mc" in game.command("list"))
        game.command("gamemode spectator aoe2mc")
        last = -1
        while b.time < END:
            me.run(1)
            sec = int(b.time)
            if sec == last:
                continue
            last = sec
            g = b.g
            pos = g.positions(sorted(g.soldiers))
            if first is None and b.targets:
                first = b.time
                print("first attack", round(b.time, 1), sorted(set(b.targets.values())), flush=True)
            row = dict(t=round(b.time, 1), stock=dict(g.stock), villagers=len(g.villagers), soldiers=sorted(g.soldiers.values()),
                       alive=len(pos), owned=sorted(train.owned(g)) if hasattr(train, "owned") else None,
                       sites=[(s["name"], bool(s.get("done"))) for s in g.sites], targets=len(b.targets),
                       p1=len(me.positions(p1)), p1_forts=len(b.forts()) if sec % 10 == 0 else None)
            if sec % 5 == 0:
                if boxes is None:
                    boxes = b.forts()
                    names = {combat.target_uuid(o["footprint"]): o["name"] for o in data["objects"] if o.get("footprint")}
                hp = {}
                for t, bx in boxes.items():
                    r = game.command(f"scoreboard players get {t} aoe_hp")
                    v = r.split(" has ")[-1].split()[0] if " has " in r else "-"
                    near = sum(bx[0] - 3 <= p[0] <= bx[3] + 4 and bx[2] - 3 <= p[2] <= bx[5] + 4 for p in pos.values())
                    hp[names[t]] = [v, near, sum(v2 == t for v2 in b.targets.values())]
                row["hp"] = hp
            log.write(json.dumps(row, default=str) + "\n"); log.flush()
            if sec % 60 == 0:
                print(json.dumps({k: row[k] for k in ("t", "stock", "villagers", "soldiers", "sites", "targets", "p1", "p1_forts")}, default=str), flush=True)
            key = next((k for k in (300, 600, 540, 660, 780) if sec >= k and k not in done), None)
            shot = key is not None and (key in (300, 600) and b.center() or key not in (300, 600) and pos)
            if shot:
                done.add(key)
                if key in (300, 600):
                    x, z = b.center(); y = g.map.y(int(x), int(z)) or 70
                else:
                    xs = [p[0] for p in pos.values()]; zs = [p[2] for p in pos.values()]
                    x, y, z = sum(xs) / len(xs), max(p[1] for p in pos.values()), sum(zs) / len(zs)
                game.command(f"tp aoe2mc {x + 12:.1f} {y + 12:.1f} {z - 12:.1f} 45 40")
                time.sleep(5)
                c.shot(os.path.join(out, f"t{key}.png"))
        print("end", b.time, "first attack", first)
        print("p1 alive", len(me.positions(p1)), "of", len(p1), "p1 forts", len(b.forts()))
