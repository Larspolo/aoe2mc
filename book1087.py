"""Check #1087, part 2: open the Timeline book of the replay end world. python3 book1087.py WORLD OUTDIR"""
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
with run.Game(world) as game, mc_shot.Client(game.game_port, game.version) as client:
    client.wait_join(lambda: "aoe2mc" in game.command("list").split(":", 1)[-1])
    time.sleep(3)
    ans = game.command('data get entity aoe2mc Inventory[{id:"minecraft:written_book"}].Slot')
    print("slot:", ans, flush=True)
    slot = int(re.search(r"(\d+)b", ans).group(1))
    if slot > 8:
        game.command(f"item replace entity aoe2mc hotbar.8 from entity aoe2mc inventory.{slot - 9}")
        slot = 8
    client.key(str(slot + 1))
    time.sleep(1)
    client.xdo("click", 3)                                             # use: open the book
    time.sleep(2)
    client.shot(os.path.join(out, "book1.png"))
    client.key("Next")                                                 # page down: the next page
    time.sleep(1)
    client.shot(os.path.join(out, "book2.png"))
    print("done", flush=True)
