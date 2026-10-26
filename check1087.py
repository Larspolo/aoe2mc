"""Check #1087: the summary at the end of the live replay with a real client (Paper 26.3).
python3 check1087.py WORLD OUTDIR"""
import json
import os
import sys
import time

ROOT = "/home/user/aoe2mc"
for d in (ROOT, os.path.join(ROOT, "game"), os.path.join(ROOT, "tools")):
    sys.path.insert(0, d)
import mc_shot  # noqa: E402
import run  # noqa: E402

world, out = sys.argv[1], sys.argv[2]
os.makedirs(out, exist_ok=True)
JUMP = 43 * 60_000 + 30_000                                            # 43:30, the record ends at 44:22


class Guide:
    """poll(control): the jump near the end once, then the hotbar input."""
    input = r = None

    def __init__(self):
        self.jumped = False

    def __call__(self, control):
        if not self.jumped:
            self.jumped = True
            control["jump"] = JUMP
            print("jump to", JUMP, flush=True)
        return self.input(control)


with run.Game(world) as game, mc_shot.Client(game.game_port, game.version, chat=True) as client:
    client.wait_join(lambda: "aoe2mc" in game.command("list").split(":", 1)[-1])
    sent, command = [], game.command
    game.command = lambda c: (sent.append(c), command(c))[1]
    t0 = time.time()
    stats = run.replay(game, world, speed=4.0, guide=Guide())
    print("replay done in", round(time.time() - t0), "s", stats, flush=True)
    with open(os.path.join(out, "sent.txt"), "w") as f:
        f.write("\n".join(c for c in sent if c.startswith(("tellraw @a", "give @a minecraft:written_book"))))
    time.sleep(2)
    client.shot(os.path.join(out, "end.png"))
    client.key("t")                                                    # the chat with its history
    time.sleep(1.5)
    client.shot(os.path.join(out, "chat.png"))
    client.key("Escape")
    time.sleep(1)
    inv = command("data get entity aoe2mc Inventory")
    print("inventory:", inv[:600], flush=True)
    import re
    m = re.search(r'\{[^{}]*Slot: (\d+)b[^{}]*id: "minecraft:written_book"', inv) or \
        re.search(r'id: "minecraft:written_book"[^{}]*Slot: (\d+)b', inv)
    if not m:                                                          # find the slot in any order of the keys
        for part in inv.split("}, {"):
            if "written_book" in part and (s := re.search(r"Slot: (\d+)b", part)):
                m = s
                break
    slot = int(m.group(1)) if m else 0
    print("book slot", slot, flush=True)
    if slot > 8:
        command(f"item replace entity aoe2mc hotbar.8 from entity aoe2mc inventory.{slot - 9}")
        slot = 8
    client.key(str(slot + 1))
    time.sleep(1)
    client.xdo("mousemove", 640, 360)
    client.xdo("click", 3)                                             # use: open the book
    time.sleep(2)
    client.shot(os.path.join(out, "book1.png"))
    client.click(640 + 3 * 50, 360 + 3 * 60)                           # the "next page" arrow (approximate)
    time.sleep(1)
    client.shot(os.path.join(out, "book2.png"))
    print("done", flush=True)
