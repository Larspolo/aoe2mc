"""Check 6 of #718: the trunk of the owner's tree (76, 49) on the hill (#1157), before and after the first chop, on
Paper with a real client. Usage: WORLD OUTDIR"""
import json, os, re, sys
ROOT = "/home/user/aoe2mc"
sys.path[:0] = [ROOT, os.path.join(ROOT, "game"), os.path.join(ROOT, "tools")]
import run, combat, replay, mc_shot  # noqa

world, out = sys.argv[1], sys.argv[2]
data = json.load(open(os.path.join(world, "aoe2mc.json")))
TILE, CAM, AT = (76, 49), (310.5, 64.6, 193.0), (305.5, 66.5, 197.5)
log, done = [], []
with run.Game(world) as game:
    game.forceload()
    combat.setup(game, data)
    with mc_shot.Client(game.game_port, game.version) as c:
        c.wait_join(lambda: "aoe2mc" in game.command("list"))
        r = replay.Replay(game, data, game.version, ai=True)

        def shoot(name):
            game.command("gamemode spectator @a")
            game.command(f"tp @a {CAM[0]} {CAM[1]} {CAM[2]} facing {AT[0]} {AT[1]} {AT[2]}")
            import time; time.sleep(2.5)
            c.shot(os.path.join(out, name))
            log.append((name, game.command("bossbar get aoe2mc:replay value")))

        def poll(control):
            now = control.get("time", 0)
            if not done and now >= 120000:
                done.append(1)
                shoot("check6-tree-before.png")
            elif len(done) == 1 and TILE in r.crew.trunks:
                done.append(2)
                (fx0, fx1, fz0, fz1), ys, _, rz = r.crew.site(TILE)
                n = r.crew.trunks[TILE]
                cells = []
                for x in range(fx1 - n, fx1):
                    ys_log = [y for y in range(min(ys) - 2, max(ys) + 3)
                              if "passed" in game.command(f"execute if block {x} {y} {rz} #minecraft:logs")]
                    solid = [y for y in ys_log if "passed" not in game.command(
                        f"execute if block {x} {y - 1} {rz} #minecraft:replaceable")]
                    cells.append((x, ys_log, solid))
                log.append(("trunk", n, rz, cells, round(now / 1000)))
                shoot("check6-trunk-after.png")
                control["jump"] = 0                                   # with rewind: stops the replay
        r.run(4.0, bar=True, poll=poll, log=None, rewind=True)
    errors = [ln for ln in game.server.log if re.search(r"ERROR|Exception|Traceback", ln) and "minecraftservices" not in ln
              and "Services are unavailable" not in ln]
    json.dump({"log": log, "errors": errors[:30]}, open(os.path.join(out, "check.json"), "w"), indent=1, default=str)
    print(json.dumps(log, default=str), "\nerrors:", len(errors), errors[:5], flush=True)
