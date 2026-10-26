"""Check 4 of #718: the jumps of the live replay (#1030), the loading text (#871) and the end (#872) on Paper with a
real client. Usage: WORLD OUTDIR"""
import json, os, re, sys, threading, time
ROOT = "/home/user/aoe2mc"
sys.path[:0] = [ROOT, os.path.join(ROOT, "game"), os.path.join(ROOT, "tools")]
import run, combat, replay, mc_shot  # noqa

world, out = sys.argv[1], sys.argv[2]
data = json.load(open(os.path.join(world, "aoe2mc.json")))
FIRST, SECOND = 17 * 60000 + 50000, 44 * 60000 + 10000
log = []
with run.Game(world) as game:
    game.forceload()
    combat.setup(game, data)
    with mc_shot.Client(game.game_port, game.version) as c:
        c.wait_join(lambda: "aoe2mc" in game.command("list"))
        stage, t0 = [0], time.time()

        def shoot(name, after):
            time.sleep(after)
            c.shot(os.path.join(out, name))
            log.append((name, round(time.time() - t0, 1), game.command("bossbar get aoe2mc:replay value")))

        def poll(control):
            now = control.get("time", 0)
            if stage[0] == 0 and time.time() - t0 > 8:                   # the view of the start is there
                stage[0] = 1
                control["jump"] = FIRST
                threading.Thread(target=shoot, args=("jump1-loading.png", 0.4)).start()
            elif stage[0] == 1 and now >= FIRST + 20000:
                stage[0] = 2
                shoot("after-jump1.png", 0)
                control["jump"] = SECOND
                threading.Thread(target=shoot, args=("jump2-loading.png", 0.4)).start()
        r = replay.Replay(game, data, game.version, ai=True)
        stats = r.run(4.0, bar=True, poll=poll, log=None)
        t_end = time.time()
        shoot("end.png", 0.5)
        log.append(("stats", stats))
        time.sleep(3)
        shoot("end-later.png", 0)
    errors = [ln for ln in game.server.log if re.search(r"ERROR|Exception|Traceback", ln) and "minecraftservices" not in ln]
    json.dump({"log": log, "errors": errors[:30]}, open(os.path.join(out, "check.json"), "w"), indent=1, default=str)
    print(json.dumps(log, default=str), "\nerrors:", len(errors), errors[:5], flush=True)
