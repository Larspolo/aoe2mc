import json, os, re, sys, time
from unittest import mock
R = "/home/user/aoe2mc"; sys.path[:0] = [R, R + "/tools", R + "/game"]
import gather, recap, run, mc_shot, demolish, repair, combat
S, W = sys.argv[1], sys.argv[2]
data = json.load(open(os.path.join(W, "aoe2mc.json")))
objs = {o.get("ref"): o for o in data["objects"] if o.get("ref") is not None}
house = objs[1]; print("house", house["name"], house.get("footprint"), file=sys.stderr)
log, shots = [], []
class Probe:
    def __init__(s, g, game, client): s.g, s.game, s.client, s.due, s.done = g, game, client, 0, set()
    def step(s):
        now = recap.game_time(s.g)
        if now < s.due: return
        s.due = now + 1
        fired = [k for k in range(20) if re.search(r" has 1\b", s.game.command(f"scoreboard players get #{k} aoe_trig"))]
        hp = s.game.command(f"scoreboard players get @e[limit=1,{combat.target_uuid(house['footprint'])[3:-1]}] aoe_hp") if False else ""
        log.append((round(now), fired, s.g.data.get("kept", None), sorted(vars(s.g).get("kept", ()))))
        print(round(now), fired, sorted(vars(s.g).get("kept", ())), file=sys.stderr)
        x0, z0, x1, z1 = house["footprint"]
        if now >= 20 and "tp" not in s.done:
            s.done.add("tp"); print(s.game.command(f"tp @e[tag=aoe2mc.r3] 21.5 66 63.5"), file=sys.stderr)
        if now >= 30 and "del1" not in s.done:
            s.done.add("del1"); log.append(("delete at 30 s", demolish.delete(s.g, 1, (x0, x1, z0, z1))))
        if now >= 85 and "del2" not in s.done:
            s.done.add("del2"); log.append(("delete at 85 s", demolish.delete(s.g, 1, (x0, x1, z0, z1))))
        for t, (pos, look) in {12: ((x0 + 4, 74, z0 + 16), (180, 30)), 16: ((32, 74, 98), (180, 30)), 22: ((74, 74, 66), (-90, 25)),
                               40: ((64, 74, 78), (180, 35)), 95: ((x0 + 4, 74, z0 + 16), (180, 30))}.items():
            if now >= t and t not in s.done:
                s.done.add(t); s.client.place(s.game, *pos, yaw=look[0], pitch=look[1], wait=4); p = f"{S}/shot{t}.png"
                s.client.key('t'); time.sleep(1); s.client.shot(p); s.client.key('Escape'); shots.append(p)
with run.Game(W) as game, mc_shot.Client(game.game_port, game.version) as client:
    orig = gather.Gather.run
    def hooked(g, seconds=None, until=None):

        g.bots = [*g.bots, Probe(g, game, client)]
        return orig(g, seconds, until=lambda: recap.game_time(g) >= 100)
    with mock.patch.object(gather.Gather, "run", hooked):
        run.play(game, W, mode="scenario", wait=True)
    open(f"{S}/chat.txt", "w").write(client.text())
    open(f"{S}/server.log", "w").write(open(os.path.join(game.folder, "logs", "latest.log")).read())
json.dump(log, open(f"{S}/log.json", "w"), default=str)
