"""#841: screenshots of the minimap frame at the spawn and of the map in the hand, real client on Paper."""
import re
import sys
import time

sys.path[:0] = ["tools", "."]
import mc_shot  # noqa: E402
from game import run  # noqa: E402

world, out = sys.argv[1], sys.argv[2]
with run.Game(world) as server, mc_shot.Client(server.game_port, server.version) as client:
    client.wait_join(lambda: "aoe2mc" in server.command("list").split(":", 1)[-1])
    time.sleep(5)
    pos = server.command("data get entity @e[type=glow_item_frame,limit=1] Pos")
    print("frame", pos, flush=True)
    x, y, z = (float(v) for v in re.findall(r"(-?\d+(?:\.\d+)?)d", pos)[:3])
    server.command("gamemode spectator aoe2mc")
    server.command(f"tp aoe2mc {x} {y + 1.2} {z + 0.9} 180 70")
    time.sleep(10)
    client.shot(f"{out}_frame.png")
    server.command(f"tp aoe2mc {x} {y + 4} {z + 4} 180 40")
    time.sleep(6)
    client.shot(f"{out}_frame_far.png")
    server.command("gamemode adventure aoe2mc")
    server.command(f"tp aoe2mc {x + 2} {y + 0.5} {z + 2} 180 0")
    time.sleep(2)
    print(server.command("item replace entity aoe2mc weapon.mainhand with filled_map[map_id=0]"), flush=True)
    server.command(f"tp aoe2mc {x + 2} {y + 0.5} {z + 2} 180 90")
    time.sleep(8)
    client.shot(f"{out}_hand.png")
    print("ok", flush=True)
