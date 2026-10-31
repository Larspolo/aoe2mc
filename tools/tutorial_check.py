#!/usr/bin/env python3
"""
Play the tutorial (run.py --play --tutorial, epic #5160) on a real Paper server from the first step to the end title
(#5228): level 4 of the verify skill.

Usage:
    python3 aoe2mc.py --random-map arabia --seed 1 OUTWorld        # trees, berries and a town center of player 1
    python3 tools/tutorial_check.py OUTWorld OUTDIR [--speed 4] [--minutes 30]

The tool copies the world, starts Paper and joins the real client (tools/mc_shot.py). A driver thread gives the input
of a person through the client: it aims with a teleport (Client.pick, mc_shot.aims) and clicks with the mouse
(xdotool): a right click with the command stick (select, gather, open a menu, attack), a click on a chest menu slot
and a right click on the ground to place a building. The game loop of run.play reads these clicks as from a person.
OUTDIR gets steps.json (the boss bar text, the chat line and the game time of each step), the screenshots and the
server log. Exit 0: the tutorial is complete.
"""
import argparse
import json
import os
import shutil
import sys
import tempfile
import threading
import time
import traceback
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path[:0] = [ROOT, HERE, os.path.join(ROOT, "game")]

import build  # noqa: E402
import gather  # noqa: E402
import mc_shot  # noqa: E402
import menu  # noqa: E402
import recap  # noqa: E402
import train  # noqa: E402
import tutorial  # noqa: E402

NAME = "aoe2mc"                                                        # the player of mc_shot.Client


class Driver:
    """The input of a person for each step of tutorial.STEPS, through the real client."""

    def __init__(self, g, client, out, minutes):
        self.g, self.c, self.out, self.end = g, client, out, time.time() + minutes * 60
        self.log, self.shots, self.error = [], [], None
        self.villager = None

    # --- helpers
    def step(self):
        return vars(self.g).get("tutorial_step") or 0

    def note(self, text):
        self.log.append({"time": recap.mmss(recap.game_time(self.g)), "step": self.step(), "event": text})
        print(f"[{self.log[-1]['time']}] step {self.step() + 1}: {text}", flush=True)

    def shot(self, name):
        path = os.path.join(self.out, name)
        self.c.shot(path)
        self.shots.append(name)
        self.note(f"screenshot {name}")

    def wait(self, n, seconds=120):
        """Wait until step n is done (the index of the step passed n); False at the time limit."""
        t = time.time() + seconds
        while self.step() <= n and time.time() < min(t, self.end) and not self.g.ended:
            time.sleep(0.5)
        return self.step() > n

    def aim(self, mid, want, button=3, dists=(3, 5, 7, 9), ground=None):
        """Teleport the player so that its eye ray hits want (the target of Gather.target) and click."""
        for stand, face in mc_shot.aims(mid, dists, ground):
            self.g.command(f"tp {NAME} {stand[0]:.2f} {stand[1]:.2f} {stand[2]:.2f} facing "
                           f"{face[0]:.2f} {face[1]:.2f} {face[2]:.2f}")
            time.sleep(0.5)
            look = self.g.look(NAME)
            if look and mc_shot.hits(self.g.target(*look, self.g.positions(sorted(self.g.pickable()))), want):
                self.c.click(self.c.size[0] // 2, self.c.size[1] // 2, button=button)
                time.sleep(2.0)                                        # gather.HOLD: a short click
                return True
        return False

    def unit(self, uuid):
        """Right click the unit uuid with the command stick."""
        return self.c.pick(self.g, uuid, dists=(3, 5, 7)) is not None

    def resource(self, tile):
        """Right click the tree or bush tile."""
        T = self.g.map.T
        x, z = (tile[0] + 0.5) * T, (tile[1] + 0.5) * T
        y = self.g.map.y(int(x), int(z)) or 64
        return self.aim((x, y + 1.0, z), tile, ground=y)

    def building(self, rect):
        """Right click the own building rect (its menu opens)."""
        return self.c.pick(self.g, tuple(rect), dists=(6, 9, 12)) is not None

    def slot(self, name):
        """Click the item name (a building, a unit or a technology) in the open menu of the player."""
        t = time.time() + 15
        while NAME not in self.g.menus and time.time() < t:
            time.sleep(0.3)
        if NAME not in self.g.menus:
            self.note(f"no menu opened for {name}")
            return False
        handler = self.g.menus[NAME]
        if hasattr(handler, "rect"):                                   # a train menu (train.show)
            slot = train.layout(self.g, handler.rect).get(name, (None,))[0]
        else:
            slot = build.MENU.index(name) if name in build.MENU else None
        if slot is None:
            self.note(f"the menu has no item {name}")
            return False
        rows = max(s for s, *_ in self.g.menu_items[NAME]) // 9 + 1
        time.sleep(1.5)                                                # the client draws the chest screen
        self.c.click(*self.c.slot(slot, rows))
        time.sleep(1.5)
        if NAME in self.g.menus and self.g.menus[NAME] is handler and not hasattr(handler, "rect"):
            self.c.key("Escape")
        return True

    def build(self, name, near):
        """Open the build menu with a right click on the selected villager, choose name, place it with a right click
        near the block cell near. Returns the site, or None."""
        g = self.g
        for _ in range(4):
            if self.villager not in g.villagers:
                self.villager = min(g.villagers)
            if self.villager not in g.selected and not self.unit(self.villager):
                continue
            if not self.unit(self.villager) or not self.slot(name):
                self.c.key("Escape")
                continue
            self.note(f"chose {build.chosen(g, NAME)} in the build menu")
            if (rect := build.near(g, name, near)) is None:
                self.note(f"no free place for {name}")
                return None
            x0, x1, z0, z1 = rect
            cell = (x0 + x1) // 2, (z0 + z1) // 2
            y = g.map.y(*cell) or 64
            sites = len(g.sites)
            g.command(f"tp {NAME} {cell[0] + 0.5} {y + 24} {cell[1] + 0.6} facing {cell[0] + 0.5} {y - 0.5} {cell[1] + 0.5}")
            time.sleep(1.0)
            self.shot(f"place_{name.lower()}_{len(self.shots)}.png")             # the ghost before the click
            self.c.click(self.c.size[0] // 2, self.c.size[1] // 2, button=3)   # a right click on the ground places it
            time.sleep(2.0)
            if len(g.sites) > sites:
                site = g.sites[-1]
                self.note(f"placed {name} at {site['footprint']}")
                return site
            self.note(f"the right click placed no {name}")
            g.cancel(NAME)
        return None

    def train(self, building, name, times=1):
        rect = next((r for r, n in train.homes(self.g).items() if n == building), None)
        for _ in range(times):
            for _ in range(3):
                if rect and self.building(rect) and self.slot(name):
                    self.note(f"clicked {name} in the menu of the {building}")
                    break
            self.c.key("Escape")
            time.sleep(1.0)

    def nearest(self, tiles, cell):
        T = self.g.map.T
        return min(tiles, key=lambda t: ((t[0] + 0.5) * T - cell[0]) ** 2 + ((t[1] + 0.5) * T - cell[1]) ** 2)

    def home(self):
        rect = next(r for r, n in train.homes(self.g).items() if n == "TOWN_CENTER")
        return rect, ((rect[0] + rect[1]) // 2, (rect[2] + rect[3]) // 2)

    def gather_at(self, tiles):
        """Select the villager and right click the nearest tile of tiles."""
        _, mid = self.home()
        tile = self.nearest(tiles, mid)
        for _ in range(4):
            if self.villager not in self.g.selected:
                self.unit(self.villager)
            if self.villager in self.g.selected and self.resource(tile):
                self.note(f"sent the villager to {tile}")
                return tile
        return None

    # --- the steps
    def run(self):
        try:
            self.play()
        except Exception:
            self.error = traceback.format_exc()
            print(self.error, flush=True)

    def play(self):
        g, (_, mid) = self.g, self.home()
        t = time.time() + 60
        while vars(g).get("tutorial_step") is None and time.time() < t:
            time.sleep(0.5)
        time.sleep(3)
        g.command(f"tp {NAME} {mid[0] + 0.5} {g.map.y(*mid) + 20} {mid[1] + 16.5} facing {mid[0] + 0.5} {g.map.y(*mid)} {mid[1] + 0.5}")
        time.sleep(4)
        self.shot("1_select.png")                                      # the boss bar of the first step
        self.villager = min(g.villagers)
        while self.step() == 0 and time.time() < self.end:             # 1 select
            self.unit(self.villager)
            self.wait(0, 5)
        trees = self.gather_at(g.map.trees)                            # 2 wood
        self.wait(1, 600)
        site = self.build("HOUSE", mid)                                # 3 house
        if self.wait(2, 600) and site:
            x0, x1, z0, z1 = site["footprint"]
            cx, cz, y = (x0 + x1) / 2, (z0 + z1) / 2, g.map.y((x0 + x1) // 2, (z0 + z1) // 2) or 64
            g.command(f"tp {NAME} {cx:.1f} {y + 8} {cz + 14:.1f} facing {cx:.1f} {y + 2} {cz:.1f}")
            time.sleep(4)
            self.shot("3_house.png")
        self.train("TOWN_CENTER", "VILLAGER")                          # 4 villager
        self.wait(3, 60)
        T = g.map.T
        if trees:
            self.build("LUMBER_CAMP", (int((trees[0] + 0.5) * T), int((trees[1] + 0.5) * T)))   # 5 camps
        bush = self.nearest(g.map.bushes, mid) if g.map.bushes else None
        if bush:
            self.build("MILL", (int((bush[0] + 0.5) * T), int((bush[1] + 0.5) * T)))
        self.wait(4, 600)
        if bush:
            self.gather_at([bush])                                     # 6 food
        self.wait(5, 900)
        self.train("TOWN_CENTER", "FEUDAL_AGE")                        # 7 feudal
        if self.wait(6, 900):
            g.command(f"tp {NAME} {mid[0] + 0.5} {g.map.y(*mid) + 20} {mid[1] + 16.5} facing {mid[0] + 0.5} {g.map.y(*mid)} {mid[1] + 0.5}")
            time.sleep(1.5)
            self.shot("7_feudal.png")
        self.build("BARRACKS", mid)                                    # 8 barracks
        self.wait(7, 600)
        self.train("BARRACKS", "MILITIA", 3)                           # 9 militia
        self.wait(8, 600)
        militia = sorted(u for u, n in g.soldiers.items() if n == "MILITIA")   # 10 camp
        g.choose(set())
        for u in militia:
            for _ in range(3):
                if u in g.selected or self.unit(u):
                    break
        self.note(f"selected {len(g.selected & set(militia))} of {len(militia)} militia")
        shot = False
        while self.step() == 9 and time.time() < self.end and not g.ended:
            camp = [u for u in vars(g).get("tutorial_camp", ()) if u in g.forts]
            if not camp:
                break
            x0, y0, z0, x1, _, z1 = g.forts[camp[0]]
            if not g.selected & set(militia):
                for u in militia:
                    if u in g.soldiers and u not in g.selected:
                        self.unit(u)
            if self.aim(((x0 + x1) / 2, y0 + 1.5, (z0 + z1) / 2), camp[0], dists=(4, 6, 8, 10), ground=y0):
                self.note(f"attack order on the camp building {camp[0]}")
            if not shot:
                time.sleep(20)
                g.command(f"tp {NAME} {(x0 + x1) / 2:.1f} {y0 + 10} {z1 + 12:.1f} facing {(x0 + x1) / 2:.1f} {y0 + 1} {(z0 + z1) / 2:.1f}")
                time.sleep(4)
                self.shot("10_camp.png")
                shot = True
            t = time.time() + 40
            while camp[0] in g.forts and time.time() < t and not g.ended:
                time.sleep(0.5)
        t = time.time() + 10
        while self.step() < len(tutorial.STEPS) and time.time() < t:
            time.sleep(0.2)
        if self.step() >= len(tutorial.STEPS):
            self.shot("11_end.png")                                    # the end title


def check(world, out, speed=4.0, minutes=30.0, version=None):
    """Play the tutorial on a copy of world; returns the result dict (also out/steps.json)."""
    import mc_check
    import run
    os.makedirs(out, exist_ok=True)
    res = {"commit": os.popen(f"git -C {ROOT} rev-parse --short HEAD").read().strip(), "speed": speed}
    with tempfile.TemporaryDirectory(dir=mc_check.workdir()) as tmp:
        copy = os.path.join(tmp, "TutorialCheck")
        shutil.copytree(world, copy)
        shown, side = [], {}
        run_, show_ = gather.Gather.run, menu.show

        def hooked(g, seconds=None, until=None):                       # run.play calls g.run after its setup
            g.menu_items = {}
            command = g.command

            def logged(cmd):                                           # the boss bar and chat lines of each step
                if cmd.startswith(f"bossbar set {tutorial.BAR} name") or cmd.startswith("tellraw @a") \
                        or cmd.startswith("title @a"):
                    shown.append({"time": recap.mmss(recap.game_time(g)), "step": vars(g).get("tutorial_step"),
                                  "command": cmd})
                return command(cmd)
            g.command = logged
            d = side["driver"] = Driver(g, side["client"], out, minutes)
            side["thread"] = threading.Thread(target=d.run, daemon=True)
            side["thread"].start()
            return run_(g, seconds, until=lambda: time.time() > d.end)

        def show(g, player, title, items, handler):                    # the slots of the open menu (its rows)
            vars(g).setdefault("menu_items", {})[player] = items
            return show_(g, player, title, items, handler)

        with run.Game(copy, version or mc_check.DEFAULT_VERSION) as game, \
                mc_shot.Client(game.game_port, game.version, chat=True) as client:
            side["client"] = client
            client.wait_join(lambda: NAME in game.command("list").split(":", 1)[-1])
            client.wait_loaded(game)
            try:
                with mock.patch.object(gather.Gather, "run", hooked), mock.patch.object(menu, "show", show):
                    run.play(game, copy, None, speed=speed, tutorial=True)
            finally:
                if "thread" in side:
                    side["thread"].join(timeout=60)
                path = os.path.join(game.folder, "logs", "latest.log")
                if os.path.isfile(path):
                    shutil.copyfile(path, os.path.join(out, "server.log"))
    d = side.get("driver")
    res.update({"steps_done": d.step() if d else 0, "of": len(tutorial.STEPS), "shown": shown,
                "events": d.log if d else [], "shots": d.shots if d else [], "error": d and d.error})
    with open(os.path.join(out, "steps.json"), "w") as f:
        json.dump(res, f, indent=1)
    return res


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0].strip(),
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("world", help="a converted world with a town center, villagers, trees and berries of player 1")
    ap.add_argument("out", help="the folder of steps.json, the screenshots and the server log")
    ap.add_argument("--speed", type=float, default=4.0, help="times the Normal game speed (default 4)")
    ap.add_argument("--minutes", type=float, default=30.0, help="stop after this real time in minutes (default 30)")
    ap.add_argument("--version", help="Minecraft version of the server")
    a = ap.parse_args(argv)
    if not os.path.isfile(os.path.join(a.world, "level.dat")):
        sys.exit(f"no level.dat in {a.world}")
    r = check(a.world, a.out, a.speed, a.minutes, a.version)
    for s in r["shown"]:
        print(f"[{s['time']}] step {s['step']}: {s['command'][:150]}")
    print(f"Steps done: {r['steps_done']}/{r['of']}. Screenshots: {', '.join(r['shots']) or 'none'}.")
    return 0 if r["steps_done"] == r["of"] else 1


if __name__ == "__main__":
    sys.exit(main())
