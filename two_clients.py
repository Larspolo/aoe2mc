"""Check #1938: a game of two people on Paper with two real clients (anna = player 1, ben = player 2)."""
import os
import shutil
import sys
import threading
import time

ROOT = "/home/user/aoe2mc"
sys.path[:0] = [ROOT, f"{ROOT}/game", f"{ROOT}/tools"]
import mc_shot  # noqa: E402
import gather  # noqa: E402
import run  # noqa: E402
import train  # noqa: E402

OUT = sys.argv[1]
WORLD = sys.argv[2]
os.makedirs(OUT, exist_ok=True)
VIL = {"anna": "e09ae956-f9b8-2dba-c5d8-412c9a029797", "ben": "2c664dd6-0fcd-951a-e801-b86b192f684b"}
TC = {"anna": (68, 68), "ben": (252, 68)}
GS, BEFORE = {}, {}
orig = gather.Gather.run


def capture(self, *a, **k):
    GS[1] = self
    for s in self.bots:
        GS[s.g.player] = s.g
    return orig(self, *a, **k)


gather.Gather.run = capture
import fog  # noqa: E402
LOOPS = []
orig_fog = fog.tick


def fog_tick(g):
    if g is GS.get(1):
        LOOPS.append(time.time())
    return orig_fog(g)


fog.tick = fog_tick


def rate():
    last = [t for t in LOOPS if t > time.time() - 30]
    return f"{len(last) / 30:.2f} loops per s (target 4)"


def log(*a):
    print(time.strftime("%H:%M:%S"), *a, flush=True)


def chat(c):
    return [line.split("[CHAT]", 1)[1].strip() for line in c.text().splitlines() if "[CHAT]" in line]


def say(c, text):
    c.key("t")
    time.sleep(1)
    c.xdo("type", "--delay", "80", text)
    time.sleep(0.5)
    c.key("Return")
    time.sleep(1)


run.Game.people = 2                                    # as main(): before the joins
with run.Game(WORLD) as game, mc_shot.Client(game.game_port, game.version, chat=True, name="anna") as a:
    a.wait_join(lambda: "anna" in game.command("list").split(":", 1)[-1])
    log("anna joined")
    with mc_shot.Client(game.game_port, game.version, chat=True, name="ben") as b:
        b.wait_join(lambda: "ben" in game.command("list").split(":", 1)[-1])
        log("ben joined", game.sides)
        t = threading.Thread(target=run.play, args=(game, WORLD),
                             kwargs=dict(cheats=True, seconds=900, people=2), daemon=True)
        t.start()
        while len(GS) < 2:
            time.sleep(1)
        time.sleep(10)
        log("gathers", {p: g.who for p, g in GS.items()}, "teams", game.command("team list p1"), game.command("team list p2"))
        clients = {"anna": a, "ben": b}
        log("loop", rate())
        for n in (1, 2, 3, 4):                                       # the wonder bars hide the selection bar
            game.command(f"bossbar set aoe2mc:wonder_p{n} visible false")
        for name, c in clients.items():                              # select the own villager with a right click
            game.command(f"execute at {VIL[name]} run tp {name} ~ ~1 ~-3 facing entity {VIL[name]}")
            time.sleep(3)
            c.xdo("click", 3)
            time.sleep(3)
            sel = GS[1 if name == "anna" else 2].selected
            log(name, "selected", sel)
            if VIL[name] not in sel:                                  # the click did not come: set the score
                game.command(f"scoreboard players set {name} aoe_use 1")
                time.sleep(3)
                log(name, "selected after score", GS[1 if name == "anna" else 2].selected)
            c.shot(f"{OUT}/{name}-select.png")
        for name, c in clients.items():                              # the other villager: no selection
            other = VIL["ben" if name == "anna" else "anna"]
            game.command(f"execute at {other} run tp {name} ~ ~1 ~-3 facing entity {other}")
            time.sleep(3)
            c.xdo("click", 3)
            time.sleep(3)
            log(name, "selected after a click on the other villager", GS[1].selected, GS[2].selected)
            c.shot(f"{OUT}/{name}-other.png")
        say(b, "ninjalui")                                            # ben: resources with the cheat code
        time.sleep(3)
        log("stocks", GS[1].stock, GS[2].stock)
        b.shot(f"{OUT}/ben-cheat.png")
        a.shot(f"{OUT}/anna-after-ben-cheat.png")
        for p in (1, 2):
            g = GS[p]
            log("before", p, "villagers", sorted(g.villagers), "soldiers", g.soldiers, "pop", g.pop)
            BEFORE[p] = set(g.villagers) | set(g.soldiers)
        log("ben queue villager", train.queue(GS[2], "ben", TC["ben"], "VILLAGER_MALE"))
        log("ben queue feudal", train.queue(GS[2], "ben", TC["ben"], "FEUDAL_AGE"))
        log("anna queue villager", train.queue(GS[1], "anna", TC["anna"], "VILLAGER_MALE"))
        log("anna queue feudal (no resources)", train.queue(GS[1], "anna", TC["anna"], "FEUDAL_AGE"))
        time.sleep(40)
        for p in (1, 2):
            g = GS[p]
            now = set(g.villagers) | set(g.soldiers)
            log("after", p, "new", now - BEFORE[p], "gone", BEFORE[p] - now, "pop", g.pop,
                "pos", g.positions(sorted(BEFORE[p] | now)))
            for u in BEFORE[p] - now:
                log("gone", u, game.command(f"data get entity {u} Health"))
        if os.environ.get("SHORT"):
            sys.exit(0)
        end = time.time() + 1200
        while "FEUDAL_AGE" not in GS[2].techs and time.time() < end:
            time.sleep(30)
            log("loop", rate(), "queues", GS[1].queues, GS[2].queues, "pop", GS[1].pop, GS[2].pop)
        log("ben techs", GS[2].techs, "anna techs", GS[1].techs)
        time.sleep(5)
        for name, c in clients.items():
            game.command(f"tp {name} {TC[name][0]} 100 {TC[name][1] + 20} facing {TC[name][0]} 70 {TC[name][1]}")
        time.sleep(5)
        for name, c in clients.items():
            c.shot(f"{OUT}/{name}-end.png")
            with open(f"{OUT}/{name}-chat.txt", "w") as f:
                f.write("\n".join(chat(c)) + "\n")
            log(name, "chat:\n  " + "\n  ".join(chat(c)))
        log("sidebar", game.command("scoreboard players list Food"))
        shutil.copy(os.path.join(game.folder, "logs", "latest.log"), f"{OUT}/server.log")
