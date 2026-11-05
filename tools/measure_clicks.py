"""
Measure the time from a real mouse input to its result in the game program (#5858, epic #5758). A real client
(mc_shot.Client, Xvfb, xdotool) plays on Paper on the tiny test scenario. For each input the tool aims the player with
`tp` (the rotation that Gather.target checks), sends the input with xdotool in a second thread and runs the game loop
(Gather.run) until the result is in the state of the game program. It prints a Markdown table: the median and the
maximum of TRIES tries of each input, and the floor (the click to the plugin score aoe_input, no game loop).
It also takes a screenshot during a held left drag and checks a left drag in the camera mode.

    python3 tools/measure_clicks.py OUT_DIR [--tries 20]

A test cannot give the table (a test gives pass or fail), so this is a tool. Own logic: none in the game.
"""
import argparse
import json
import math
import os
import shutil
import statistics
import sys
import threading
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path[:0] = [ROOT, os.path.join(ROOT, "tools"), os.path.join(ROOT, "game")]
import mc_shot  # noqa: E402

from game import build, camera, gather, menu, run  # noqa: E402

NAME = "aoe2mc"
EYE = 1.62
DEG = 0.15                                                         # degrees of yaw per pixel of xdotool (default sensitivity)
TIMEOUT = 5.0                                                      # seconds: a try with no result fails


def rotation(eye, point):
    """(yaw, pitch) of a look from eye at point, as gather.direction reads it."""
    dx, dy, dz = (point[i] - eye[i] for i in range(3))
    yaw = math.degrees(math.atan2(-dx, dz))
    return yaw, math.degrees(-math.atan2(dy, math.hypot(dx, dz)))


class Bench:
    def __init__(self, game, client, g):
        self.game, self.client, self.g = game, client, g

    def stand(self, x, z, point):
        """Put the player on a stone block at (x, z) above the ground, looking at point. Returns (eye, d)."""
        y = self.g.map.y(math.floor(x), math.floor(z)) + 1
        self.game.command(f"setblock {math.floor(x)} {y - 1} {math.floor(z)} minecraft:stone")
        eye = (x, y + EYE, z)
        yaw, pitch = rotation(eye, point)
        self.game.command(f"tp {NAME} {x} {y} {z} {yaw:.2f} {pitch:.2f}")
        return eye, gather.direction(yaw, pitch)

    def timed(self, act, done):
        """Seconds from act() (the input, in a thread) to done() in the game loop, or None."""
        t0 = []

        def go():
            time.sleep(0.3)
            t0.append(time.monotonic())
            act()
        th = threading.Thread(target=go)
        th.start()
        self.g.run(seconds=TIMEOUT, until=lambda: bool(t0) and done())
        th.join()
        t1 = time.monotonic()
        menu.close(self.g, NAME)                                       # a wrong pick can open a menu: close it
        return t1 - t0[0] if done() else None

    def hold(self, xz, y, a, b):
        """Stand at xz (on the ground, or at height y: the camera floor), look at corner a, hold the left button and
        turn the look to corner b (the same distance: xz is on the line between them). The button stays down."""
        if y is None:
            eye, _ = self.stand(*xz, a)
        else:
            eye = (xz[0], y + EYE, xz[1])
            self.game.command(f"tp {NAME} {xz[0]} {y} {xz[1]} {rotation(eye, a)[0]:.2f} {rotation(eye, a)[1]:.2f}")
        time.sleep(0.8)
        turn = (rotation(eye, b)[0] - rotation(eye, a)[0] + 180) % 360 - 180
        self.client.xdo("mousedown", 1)
        for _ in range(10):                                            # mouse right: the yaw grows
            self.client.xdo("mousemove_relative", "--", round(turn / 10 / DEG), 0)
            self.g.run(seconds=0.1)
        self.g.run(seconds=0.5)

    def floor(self):
        """Seconds from a right click to the score aoe_input of the plugin (RCON polls, no game loop)."""
        self.game.command(f"scoreboard players reset {NAME} {gather.INPUT_SCORE}")
        t0 = time.monotonic()
        self.client.xdo("click", 3)
        while time.monotonic() - t0 < TIMEOUT:
            if "has 1" in self.game.command(f"scoreboard players get {NAME} {gather.INPUT_SCORE}"):
                return time.monotonic() - t0
        return None


def table(rows):
    out = ["| Input | Tries | Median (ms) | Maximum (ms) | Fails |", "|---|---|---|---|---|"]
    for name, times in rows:
        ok = [t * 1000 for t in times if t is not None]
        med, top = (f"{statistics.median(ok):.0f}", f"{max(ok):.0f}") if ok else ("-", "-")
        out.append(f"| {name} | {len(times)} | {med} | {top} | {len(times) - len(ok)} |")
    return "\n".join(out)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    ap.add_argument("out")
    ap.add_argument("--tries", type=int, default=20)
    ap.add_argument("--world", help="a converted tiny world (else: convert the tiny scenario)")
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    world = os.path.join(a.out, "W")
    shutil.rmtree(world, ignore_errors=True)
    if a.world:
        shutil.copytree(a.world, world)
    else:
        import scenarios

        import aoe2mc
        aoe2mc.convert(scenarios.tiny(os.path.join(a.out, "tiny.aoe2scenario")), world)
    data = json.load(open(os.path.join(world, "aoe2mc.json")))
    rows, notes = [], []
    with run.Game(world) as game, mc_shot.Client(game.game_port, game.version) as client:
        client.wait_join(lambda: NAME in game.command("list").split(":", 1)[-1])
        client.wait_loaded(game)
        time.sleep(5)
        game.forceload()
        g = gather.Gather(game, data).setup()
        g.clicks()                                                     # gives the stick and the camera item
        game.command(f"gamemode creative {NAME}")
        game.command("gamerule doDaylightCycle false")
        b = Bench(game, client, g)
        v = next(iter(g.villagers.values()))
        client.key("1")
        g.stock.update(wood=10 ** 6, food=10 ** 6, gold=10 ** 6, stone=10 ** 6)

        def put(x, z):
            y = g.map.y(math.floor(x), math.floor(z)) + 1
            game.command(f"aoe stop {v.uuid}")                         # the plugin path of an old order ends
            game.command(f"tp {v.uuid} {x} {y} {z}")
            v.pos = (x, float(y), z)
            v.state, v.goal, v.tree, v.path, v.site, v.prey = "idle", None, None, [], None, None   # no old order
            return y

        def state():
            return v.state, v.goal, v.tree, len(v.path), v.site

        # the floor of the harness
        vx, vz = 46.5, 70.5
        vy = put(vx, vz)
        b.stand(vx + 6, vz + 6, (vx + 3, vy - 1, vz + 9))
        time.sleep(1)
        rows.append(("Floor: right click to the score aoe_input", [b.floor() for _ in range(a.tries)
                                                                    if not time.sleep(0.4)]))

        # a left click on an own unit
        times = []
        for _ in range(a.tries):
            put(vx, vz)
            g.choose(set())
            b.stand(vx + 2.5, vz + 1.5, (vx, vy + 1, vz))         # in the entity reach of the client
            time.sleep(0.5)
            times.append(b.timed(lambda: client.xdo("click", 1), lambda: g.selected == {v.uuid}))
        rows.append(("Left click on an own unit (selected)", times))

        # a right click on the ground: the walk order
        times = []
        for i in range(a.tries):
            put(vx, vz)
            g.choose({v.uuid})
            b.stand(vx + 5, vz + 5, (vx + 4 + i % 3, vy - 0.5, vz - 3))   # the ray passes east of the villager
            time.sleep(0.5)
            s0 = state()
            times.append(b.timed(lambda: client.xdo("click", 3), lambda: state() != s0))
        rows.append(("Right click on the ground (walk order)", times))

        # a right click on a tree with a villager: the gather order
        tile = next(iter(g.map.trees))
        tx, tz = tile[0] * 4 + 2, tile[1] * 4 + 2
        ty = g.map.y(tx, tz)
        times = []
        for _ in range(a.tries):
            put(tx + 6.5, tz + 0.5)
            g.choose({v.uuid})
            eye, d = b.stand(tx + 8.5, tz + 6.5, (tx, ty + 2, tz))
            if (g.target(eye, d, g.positions(sorted(g.pickable()))) or ("?",))[0] != "tree":
                notes.append("the aim at the tree did not pick the tree")
            time.sleep(0.5)
            times.append(b.timed(lambda: client.xdo("click", 3), lambda: v.tree is not None))
        rows.append(("Right click on a tree with a villager (gather order)", times))

        # the release of a left drag: the box from 2 blocks north-east to 2 blocks south-west of the villager
        times = []
        corners = (vx + 2, vy - 0.5, vz - 2), (vx - 2, vy - 0.5, vz + 2)
        for i in range(a.tries + 1):
            put(vx, vz)
            g.choose(set())
            g.run(seconds=0.3)
            b.hold((vx + 6.5, vz + 6.5), None, *corners)
            if i == 0:                                                 # the screenshot of a held drag
                client.shot(os.path.join(a.out, "drag.png"))
                client.xdo("mouseup", 1)
                g.run(seconds=1.5)
                continue
            times.append(b.timed(lambda: client.xdo("mouseup", 1), lambda: bool(g.selected)))   # soldiers win (#5761)
        rows.append(("Release of a left drag (selection tags set)", times))

        # a left click with a chosen building: the foundation
        times, cells = [], []
        for x in range(10, 90, 10):
            for z in range(10, 90, 10):
                rect = build.area(g, "HOUSE", (x, z))
                if build.free(g, rect) and build.level(g, "HOUSE", rect) and math.dist((x, z), (vx, vz)) > 8:
                    cells.append((x, z))
        for x, z in cells[:a.tries]:
            put(vx, vz)
            g.choose(set())
            game.command(f"scoreboard players set {NAME} {build.OBJECTIVE} {build.MENU.index('HOUSE') + 1}")
            b.stand(x + 4.5, z + 4.5, (x + 0.5, g.map.y(x, z) + 1, z + 0.5))
            time.sleep(0.5)
            n = len(g.sites)
            times.append(b.timed(lambda: client.xdo("click", 1), lambda: len(g.sites) > n))
            if len(g.sites) == n:
                notes.append(f"no foundation at {x} {z}")
        rows.append(("Left click with a chosen building (foundation placed)", times))

        # a left drag in the camera mode
        put(vx, vz)
        g.choose(set())
        client.key("2")                                                # the camera item: a right click turns the mode on
        time.sleep(0.5)
        client.xdo("click", 3)
        g.run(seconds=1.5)
        client.key("1")                                                # the stick: Drag gives the camera reach (Camera#reach)
        top = camera.floor(g)[0]
        g.run(seconds=1)
        b.hold((vx + 16.5, vz + 16.5), top + 1, *corners)
        client.shot(os.path.join(a.out, "camera_drag.png"))
        client.xdo("mouseup", 1)
        g.run(seconds=1.5)
        notes.append(f"camera mode drag: {len(g.selected)} units selected: " + ("PASS" if g.selected else "FAIL"))
        camera.click(g, NAME)
    text = table(rows) + "\n\n" + "\n".join(f"- {n}" for n in dict.fromkeys(notes))
    print(text)
    open(os.path.join(a.out, "timing.md"), "w").write(text + "\n")


if __name__ == "__main__":
    main()
