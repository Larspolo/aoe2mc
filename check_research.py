"""Check of #843: the Loom research of player 2 (de-64.3, 6:34) on Paper, with a real client. Usage: WORLD OUTDIR"""
import json, os, sys, threading, time
ROOT = "/home/user/aoe2mc"
sys.path[:0] = [ROOT, os.path.join(ROOT, "game"), os.path.join(ROOT, "tools")]
import run, replay, mc_shot  # noqa

world, out = sys.argv[1:3]
data = json.load(open(os.path.join(world, "aoe2mc.json")))
data["timeline"] = [e for e in data["timeline"] if 392000 <= e["time"] <= 395000] + \
    [{"time": 412000, "player": 1, "kind": "chat", "text": "check end"}]
with run.Game(world) as g:
    g.forceload()
    with mc_shot.Client(g.game_port, g.version) as c:
        c.wait_join(lambda: "aoe2mc" in g.command("list"))
        time.sleep(5)
        g.command("gamemode spectator aoe2mc")
        r = replay.Replay(g, data, g.version, ai=True)
        y = r.grid().y(368, 140) or 70
        g.command(f"tp aoe2mc 368.5 {y + 14} 150.5 180 22")
        time.sleep(10)
        t = threading.Thread(target=lambda: print(r.run(1.0, 392000, log=None)))
        t.start()
        time.sleep(3.5)                                          # the research is at 2 s
        print("during:", g.command("execute if entity @e[type=text_display,tag=aoe2mc.effect]"))
        print(g.command("data get entity @e[type=text_display,tag=aoe2mc.effect,limit=1] text"))
        c.shot(os.path.join(out, "loom.png"))
        time.sleep(11)
        print("after:", g.command("execute if entity @e[type=text_display,tag=aoe2mc.effect]"))
        c.shot(os.path.join(out, "loom_after.png"))
        t.join()
