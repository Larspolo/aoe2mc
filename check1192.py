"""Check #1192: the team sidebar and the summary at the end of the live replay of a 2 vs 2 game (Paper 26.3).
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
JUMP = 22 * 60_000                                                     # 22:00, the record ends at 23:28


class Guide:
    """poll(control): the jump near the end once, then the hotbar input."""
    input = r = None

    def __init__(self):
        self.jumped, self.shot, self.t = False, False, None

    def __call__(self, control):
        if not self.jumped:
            self.jumped = True
            control["jump"] = JUMP
            print("jump to", JUMP, flush=True)
        elif not self.shot:
            self.t = self.t or time.time()
            if time.time() - self.t > 12:                              # the sidebar after the jump, during the replay
                self.shot = True
                client.shot(os.path.join(out, "sidebar.png"))
                print("sidebar:", game.command("scoreboard objectives list")[:300], flush=True)
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
    slot = next((k for k in range(36) if "passed" in command(
        f"execute if items entity aoe2mc {'hotbar.%d' % k if k < 9 else 'inventory.%d' % (k - 9)} minecraft:written_book")),
        0)                                                             # the slot of the timeline book
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
