"""Check #1239: the live minimap of the replay (Paper 26.3, real client). python3 check1239.py WORLD OUTDIR"""
import os
import re
import sys
import time

ROOT = "/home/user/aoe2mc"
for d in (ROOT, os.path.join(ROOT, "game"), os.path.join(ROOT, "tools")):
    sys.path.insert(0, d)
import mc_shot  # noqa: E402
import run  # noqa: E402

world, out = sys.argv[1], sys.argv[2]
os.makedirs(out, exist_ok=True)
mc_shot.OPTIONS["renderDistance"] = "12"
NUM = r"-?\d+(?:\.\d+)?"


class Done(Exception):
    pass


class Guide:
    input = r = None

    def __init__(self):
        self.todo = [(30_000, "0030"), (600_000, "1000")]

    def __call__(self, control):
        if self.todo and control.get("time", 0) >= self.todo[0][0]:
            self.look(self.todo.pop(0)[1])
            if not self.todo:
                raise Done
        return self.input(control)

    def look(self, tag):
        c = game.command
        print(tag, "offhand test:", repr(c("execute if items entity aoe2mc weapon.offhand minecraft:filled_map")), flush=True)
        if tag == "0030":
            c("item replace entity aoe2mc hotbar.4 from entity aoe2mc weapon.offhand")
            c("item replace entity aoe2mc weapon.offhand with minecraft:air")
        client.key("5")
        c("execute as aoe2mc at @s run tp @s ~ ~ ~ 0 70")
        time.sleep(3)                                                 # the plugin sends the map once per second
        client.shot(os.path.join(out, f"map{tag}.png"))
        print(tag, "player", c("data get entity aoe2mc Pos"), c("data get entity aoe2mc Inventory")[:900], flush=True)
        units = [v for v in list(self.r.units.values()) if getattr(v, "uuid", None)]
        for v in units[::max(1, len(units) // 6)][:6]:
            m = re.findall(NUM, c(f"data get entity {v.uuid} Pos").rsplit(":", 1)[-1])
            if len(m) < 3:
                continue
            x, z = float(m[0]), float(m[2])
            team = next((t for t in range(1, 9) if "passed" in c(f"execute as {v.uuid} if entity @s[team=p{t}]")), None)
            print(tag, "unit", getattr(v, "name", type(v).__name__), "team", team, "pos", x, z,
                  "|", c(f"aoe minimap pixel {int(x)} {int(z)}"), flush=True)


with run.Game(world) as game, mc_shot.Client(game.game_port, game.version) as client:
    client.wait_join(lambda: "aoe2mc" in game.command("list").split(":", 1)[-1])
    try:
        run.replay(game, world, speed=4.0, guide=Guide())
    except Done:
        print("done", flush=True)
