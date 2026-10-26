"""Check of #845: the red order marker of an attack ORDER of the live replay on Paper, with a real client."""
import json, shutil, sys, time
R = "/home/user/aoe2mc"
sys.path[:0] = [R, R + "/game", R + "/tools", R + "/tests"]
import threading
import combat, mc_shot, replay  # noqa


def held(game, client, cmds, path):
    """Send the marker commands again each 0.2 s for 3 s and take the shot after 1.5 s: the software renderer of
    Xvfb draws few frames, and dust and the glowing effect last about 1 second."""
    stop = threading.Event()
    def loop():
        while not stop.is_set():
            for c in cmds:
                game.command(c)
            time.sleep(0.2)
    t = threading.Thread(target=loop)
    t.start()
    time.sleep(1.5)
    client.shot(path)
    stop.set()
    t.join()
from game import run  # noqa

S = sys.argv[1]
world = shutil.copytree(S + "/battleW", S + "/battleW_mark", dirs_exist_ok=True)
data = json.load(open(world + "/aoe2mc.json"))
ref = lambda name, p, k=0: [o for o in data["objects"] if o["kind"] == "unit" and o["name"] == name and o["player"] == p and o.get("ref") is not None][k]
res = []
with run.Game(world) as game, mc_shot.Client(game.game_port, game.version) as client:
    client.wait_join(lambda: "aoe2mc" in game.command("list").split(":", 1)[-1])
    game.forceload()
    print("targets:", combat.setup(game, data), flush=True)
    for c in ("gamemode spectator aoe2mc", "time set noon", "gamerule advance_time false"):
        game.command(c)
    r = replay.Replay(game, dict(data, timeline=[]), ai=True)
    m = r.grid()
    stable = r.refs[390]
    x0, z0, x1, z1 = stable["footprint"]
    a, b = ref("CHAMPION", 1, 0), ref("CHAMPION", 1, 1)
    y = lambda x, z: m.y(int(x), int(z)) or 0
    game.command(f"tp {a['uuid']} {x0 - 6.5} {y(x0 - 7, z0 - 4)} {z0 - 4.5}")
    time.sleep(1)
    r.units[a["ref"]].pos = (x0 - 6.5, y(x0 - 7, z0 - 4), z0 - 4.5)
    cx, cz = (x0 + x1) / 2, (z0 + z1) / 2
    game.command(f"tp aoe2mc {cx - 12} {y(cx, cz) + 9} {cz - 12} facing {cx} {y(cx, cz)} {cz}")
    time.sleep(8)
    cmds = r.commands(dict(time=0, player=1, kind="order", objects=[a["ref"]], target=390))
    ans = [game.command(c) for c in cmds]
    held(game, client, r.target_mark(dict(target=390)), f"{S}/check/mark_building.png")
    res.append(("building", cmds, ans))
    # a unit target
    p = next(o for o in data["objects"] if o["kind"] == "unit" and o["player"] == 2 and o.get("ref") is not None
             and "passed" in game.command(f"execute if entity {o['uuid']}"))
    print("target unit:", p["name"], p["uuid"], flush=True)
    X, Z = x0 - 20, z0 - 30
    game.command(f"tp {b['uuid']} {X + 0.5} {y(X, Z)} {Z + 0.5}")
    print("tp:", game.command(f"tp {p['uuid']} {X + 0.5} {y(X, Z + 44)} {Z + 44.5}"), flush=True)
    game.command(f"data merge entity {p['uuid']} {{NoAI:1b}}")
    game.command(f"effect give {p['uuid']} minecraft:resistance 30 4 true")   # it must live for the shot
    time.sleep(1)
    r.units[b["ref"]].pos = (X + 0.5, y(X, Z), Z + 0.5)
    r.units[p["ref"]].pos = (X + 0.5, y(X, Z + 44), Z + 12.5)
    pp = g_pos = game.command(f"data get entity {p['uuid']} Pos")
    print("pos:", pp[:120], flush=True)
    import re as _re
    px, py, pz = [float(v) for v in _re.findall(r"(-?[\d.]+)d", pp)]
    game.command(f"tp aoe2mc {px + 3.5} {py + 2.0} {pz - 4.0} facing {px} {py + 1.2} {pz}")
    time.sleep(8)
    cmds = r.commands(dict(time=0, player=1, kind="order", objects=[b["ref"]], target=p["ref"]))
    ans = [game.command(c) for c in cmds]
    print("glow now:", game.command(f"data get entity {p['uuid']} active_effects")[:120], flush=True)
    held(game, client, r.target_mark(dict(target=p["ref"])), f"{S}/check/mark_unit.png")
    print("glow:", game.command(f"data get entity {p['uuid']} active_effects")[:160], flush=True)
    res.append(("unit", cmds, ans))
    # a walk order: no marker
    cmds = r.commands(dict(time=0, player=1, kind="move", objects=[b["ref"]], tile=[X / 4 - 2, Z / 4]))
    res.append(("walk", cmds, [game.command(c) for c in cmds]))
json.dump(res, open(f"{S}/check/result.json", "w"), indent=1)
for k, cmds, ans in res:
    print(k, len(cmds), [c[:60] for c in cmds], "errors:", [x for x in ans if "<--[HERE]" in x or "Unknown" in x])
