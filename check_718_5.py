"""Check 5 of #718: the walk of a villager to its tree, the felled trunk on a slope (#1124) and the end of a
5-minute jump (#1125) on Paper with a real client. Usage: WORLD OUTDIR"""
import json, math, os, re, sys, threading, time
ROOT = "/home/user/aoe2mc"
sys.path[:0] = [ROOT, os.path.join(ROOT, "game"), os.path.join(ROOT, "tools")]
import run, combat, replay, mc_shot  # noqa

world, out = sys.argv[1], sys.argv[2]
data = json.load(open(os.path.join(world, "aoe2mc.json")))
WALK0, WALK1, TRUNKS = 150000, 200000, 300000          # walk log 2:30 to 3:20, trunk test at 3:35
JUMP_TO = TRUNKS + 300000                               # a 5-minute jump
NUM = r"-?\d+(?:\.\d+)?"
log, walks, bars, trunks, shots = [], {}, [], [], []
with run.Game(world) as game:
    game.forceload()
    combat.setup(game, data)
    with mc_shot.Client(game.game_port, game.version) as c:
        c.wait_join(lambda: "aoe2mc" in game.command("list"))
        r = replay.Replay(game, data, game.version, ai=True)
        stage, t0 = [0], time.time()

        def pos(uuid):
            m = re.findall(NUM, game.command(f"data get entity {uuid} Pos").rsplit(":", 1)[-1])
            return tuple(float(a) for a in m) if len(m) == 3 else None

        def shoot(name, at=None, look=None):
            if at:
                game.command("gamemode spectator @a")
                game.command(f"tp @a {at[0]:.1f} {at[1]:.1f} {at[2]:.1f} facing {look[0]:.1f} {look[1]:.1f} {look[2]:.1f}")
                time.sleep(2.5)
            c.shot(os.path.join(out, name))
            log.append((name, round(time.time() - t0, 1), game.command("bossbar get aoe2mc:replay value")))

        def test_trunks():
            g = r.crew
            for tile, n in list(g.trunks.items()):
                (fx0, fx1, fz0, fz1), ys, (sx, sz), rz = g.site(tile)
                cells = []
                for x in range(fx1 - n, fx1):
                    found = None
                    for y in range(min(ys) - 3, max(ys) + 4):
                        if "passed" in game.command(f"execute if block {x} {y} {rz} #minecraft:logs"):
                            below = game.command(f"execute if block {x} {y - 1} {rz} #minecraft:replaceable")
                            bar = game.command(f"execute if block {x} {y - 1} {rz} minecraft:barrier")
                            found = (y, "passed" not in below and "passed" not in bar)
                            break
                    cells.append((x, found))
                trunks.append({"slope": min(ys) != max(ys), "tile": tile, "logs": n, "ys": (min(ys), max(ys)), "row": rz, "cells": cells})

        def poll(control):
            now = control.get("time", 0)
            if WALK0 <= now <= WALK1 and int(now / 2000) not in walks:   # every 2 game seconds
                walks[int(now / 2000)] = {i: (v.tree, pos(v.uuid)) for i, v in r.units.items()
                                          if v.tree in r.map.trees}
            if not shots and now >= 185000:
                shots.append(1)
                v = next((v for v in r.units.values() if v.tree in r.map.trees and pos(v.uuid)), None)
                if v and (p := pos(v.uuid)):
                    tx, tz = v.tree[0] * 4 + 2, v.tree[1] * 4 + 2
                    shoot("check5-walk-work.png", (p[0] + (p[0] - tx) * 0.6 + 2, p[1] + 3, p[2] + (p[2] - tz) * 0.6 + 2), (tx, p[1] + 1, tz))
                    log.append(("work", v.uuid, v.tree, p))
            if stage[0] == 0 and now >= TRUNKS:
                stage[0] = 1
                test_trunks()
                slope = [t for t in trunks if t["slope"] and any(f for _, f in t["cells"])] or [t for t in trunks if any(f for _, f in t["cells"])]
                log.append(("working", len(r.working), "trunks", len(r.crew.trunks)))
                if slope:
                    t = slope[0]
                    x, (y, _) = next((x, f) for x, f in t["cells"] if f)
                    shoot("check5-trunk-slope.png", (x - 5, y + 4, t["row"] + 6), (x, y, t["row"]))
                control["jump"] = JUMP_TO
                stage[0], stage.append(time.time())

                def sample():
                    for _ in range(40):
                        bars.append((round(time.time() - stage[1], 1), game.command("bossbar get aoe2mc:replay value")))
                        time.sleep(0.5)
                threading.Thread(target=sample).start()
            elif stage[0] == 1 and time.time() - stage[1] > 22:
                stage[0] = 2
                control["jump"] = 0                                  # with rewind: stops the replay
        stats = r.run(4.0, bar=True, poll=poll, log=None, rewind=True)
        log.append(("stats", stats))
    errors = [ln for ln in game.server.log if re.search(r"ERROR|Exception|Traceback", ln) and "minecraftservices" not in ln
              and "Services are unavailable" not in ln]
    json.dump({"log": log, "walks": walks, "bars": bars, "trunks": trunks, "errors": errors[:30]},
              open(os.path.join(out, "check.json"), "w"), indent=1, default=str)
    print(json.dumps(log, default=str), "\nbars:", bars, "\ntrunks:", len(trunks), "\nerrors:", len(errors), errors[:5],
          flush=True)
