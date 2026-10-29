#!/usr/bin/env python3
"""
Play one full game of player 1 against the bot with a script (#3324): release check `play-check-game` of
docs/RELEASE.md.

Usage:
    python3 aoe2mc.py --random-map arabia --seed 1 OUTWorld       # the resources of a real game (#3544)
    python3 tools/play_check.py OUTWorld [--speed 2] [--minutes 40] [--log F.jsonl] [--server-log F.log] [--json F.json]

The tool copies the world (the game changes it), starts Paper without a client and plays `run.play(..., bot=True)`:
the bot of game/bot.py plays player 2 and attacks player 1 at `--bot-attack`. Player 1 gets the orders of a person from
Driver, the same bot over the Gather of player 1 (bot.Bot with `own`): it gathers, builds, trains, goes up to the
Feudal and the Castle Age, defends its town center and attacks the bot in the Castle Age. The game ends with a win, a
loss (the AoE2 conquest, game/conquest.py) or at `--minutes` of game time.

Each STEP game seconds Watch samples the units with an order: a villager that walks (state "to_...") and a soldier with
a target. A unit is stuck when it keeps the same order, moves less than MOVED blocks and is not at its target for
STUCK game seconds. At the end the tool prints the end, the game time, the age and the age times of each player, the
units, the stuck units and the exceptions of the server log.
"""
import argparse
import json
import math
import os
import re
import shutil
import sys
import tempfile
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path[:0] = [ROOT, HERE, os.path.join(ROOT, "game")]

import ai  # noqa: E402
import bot  # noqa: E402
import build  # noqa: E402
import combat  # noqa: E402
import garrison  # noqa: E402
import gather  # noqa: E402
import recap  # noqa: E402
import train  # noqa: E402

AGES = {"FEUDAL_AGE": 20, "CASTLE_AGE": 25}                        # the ages of the driver: villagers before each one
STEP, STUCK, MOVED = 5.0, 60.0, 1.0                                # game seconds, game seconds, blocks
HOME = 12                                                          # tiles: a foe unit this near the town center attacks
ERROR = re.compile(r"Exception|ERROR\]|Caused by:")                # the lines of a server or plugin exception
OFFLINE = re.compile(r"minecraftservices\.com|Services are unavailable")   # no Mojang services in a cloud session
TIME = re.compile(r"^\[\d\d:\d\d:\d\d ")                                # the time of a log line


class Driver(bot.Bot):
    """The orders of a person for player 1: the bot of game/bot.py over the Gather of player 1 (own), with the ages,
    two Feudal Age buildings for the Castle Age, a defense of the town center (the soldiers and the town bell) and an
    attack in the Castle Age."""
    order = bot.ORDER + ("ARCHERY_RANGE", "BLACKSMITH")                # 2 of the Feudal Age: CASTLE_AGE "requires"

    def __init__(self, g, foe, villagers=30, group=8):
        super().__init__(g.game, g.data, player=g.player, share=foe, villagers=villagers, attack=math.inf,
                         foe=foe.player, group=group, own=g)
        self.saving = None                                             # the age that the resources go to
        self.foes, self.rung = {}, None                                # foe soldiers near home, the belled town center
        self.guards = 0                                                # own soldiers with an attack (defend)
        self.ready = None                                              # the age whose villager number was there (#3544)
        self.bells = []                                                # [start, end] game times of the rung bell (#3561)

    def step(self):
        """Only the orders: Gather.run steps the Gather of player 1 itself."""
        self.orders()

    def orders(self):
        if self.attack == math.inf and "CASTLE_AGE" in self.g.techs:   # a person attacks with the Castle Age army
            self.attack = self.time
        if self.time < self.attack and self.time >= self.looked + bot.LOOK:
            self.looked = self.time
            self.defend()
            self.bell()
        if self.rung:                                                  # the villagers wait in the town center,
            self.drill()                                               # the barracks trains defenders (#3561)
            self.time += self.g.tick * gather.NORMAL
            return
        self.advance()
        super().orders()

    def advance(self):
        """Research the next age at the town center when its buildings and villagers are there (AGES, as an AoE2
        build order); until then save for it."""
        g = self.g
        age = next((a for a in AGES if a not in g.techs and not train.queued(g, a)), None)
        if age and len(g.villagers) >= AGES[age]:                       # a dead villager does not stop the saving
            self.ready = age
        self.saving = age if age and self.ready == age and train.missing(g, age) is None \
            and not build.locked(g, age) else None
        tc = next((r for r, n in sorted(train.homes(g).items()) if n == "TOWN_CENTER"), None)
        if self.saving and tc and all(g.stock[r] >= v for r, v in train.price(g, age).items()):
            train.queue(g, self.nobody, (tc[0], tc[2]), age)

    def recruit(self):
        if not self.saving:                                            # a person stops the queues for the next age
            super().recruit()
        elif self.foes:                                                # but trains defenders in a raid (#3561)
            self.drill()

    def drill(self):
        """Keep bot.QUEUED soldiers in the queue of each military building, not villagers at the town center: the
        defense of a person while the town bell rings or a raid comes during the saving (#3561)."""
        g = self.g
        for rect, name in sorted(train.homes(g).items()):
            units = [] if name == "TOWN_CENTER" else \
                [n for n in train.trains(g, name) if gather.military(n) and n not in train.TECHS and not build.locked(g, n)]
            for n in units[:1]:
                while len(g.queues.get(rect, [])) < bot.QUEUED and all(g.stock[r] >= v for r, v in train.price(g, n).items()) \
                        and train.queue(g, self.nobody, (rect[0], rect[2]), n):
                    pass

    def shares(self):
        """While it saves for an age, the shares follow the price of the age (#3561), with bot.WOOD for farms and
        houses, as Bot.shares does for the army; else Bot.shares."""
        if not self.saving:
            return super().shares()
        cost = train.price(self.g, self.saving)
        total = sum(cost.values())
        return {r: (bot.WOOD if r == "wood" else 0) + (1 - bot.WOOD) * cost.get(r, 0) / total for r in bot.SHARE}

    def defend(self):
        """Each soldier without a target attacks the nearest foe unit within HOME tiles of the own town center."""
        g, T = self.g, self.g.map.T
        center = self.center()
        if center is None:
            return
        self.foes = foes = {u: p for u, p in g.positions(sorted(self.share.soldiers)).items()
                            if math.dist((p[0], p[2]), center) <= HOME * T}
        mine = g.positions(sorted(u for u, n in g.soldiers.items() if combat.stats(n).attack))   # no transport ship
        self.guards = len(mine)
        live = {t for t in set(self.targets.values()) if t in foes}
        self.targets = {u: t for u, t in self.targets.items() if u in mine and t in live}
        for u in sorted(mine.keys() - self.targets.keys()):
            if ok := [k for k in foes if self.reach(u, mine[u], foes[k])]:
                t = min(ok, key=lambda k: (math.dist(foes[k], mine[u]), k))
                self.targets[u] = t
                ai.attack(g.game, [u], [g.soldiers[u]], T, t, [gather.NORMAL * train.speed(g, g.soldiers[u], u)])


    def bell(self):
        """The town bell of a person (garrison.py): the villagers go into the town center while the foe soldiers near
        it are more than the own soldiers (defend, a raid), and come out when they are not."""
        g = self.g
        raid = len(self.foes) > self.guards
        tc = next((r for r, n in sorted(garrison.holders(g).items()) if n["name"] == "TOWN_CENTER"), None)
        if raid and not self.rung and tc and g.villagers:
            g.selected = set(g.villagers)
            self.rung = garrison.order(g, self.nobody, (tc[0], tc[2]))
            g.selected = set()
            if self.rung:
                self.bells.append([recap.game_time(g), None])
        elif not raid and self.rung:
            garrison.out(g, self.rung)
            for u, v in g.villagers.items():                           # the ones that did not get in
                if v.state == "garrison":
                    v.state = "idle"
                    vars(g).get("entering", {}).pop(u, None)
            self.rung = None
            if self.bells:
                self.bells[-1][1] = recap.game_time(g)


def states(g):
    """The villager states of g as `state/resource` counts, for example "idle/wood 6, to_tree/wood 2"."""
    n = {}
    for v in g.villagers.values():
        n[f"{v.state}/{v.res}"] = n.get(f"{v.state}/{v.res}", 0) + 1
    return ", ".join(f"{k} {c}" for k, c in sorted(n.items()))


class Watch:
    """Samples the units with an order each STEP game seconds and finds the stuck ones (step(): one of Gather.bots)."""

    def __init__(self, g, sides):
        self.g, self.sides, self.due, self.shown = g, sides, 0.0, 0.0
        self.last = {}                                                 # uuid -> (order, position, game time since)
        self.stuck = {}                                                # uuid -> {player, unit, order, at, seconds}

    def step(self):
        now = recap.game_time(self.g)
        if now < self.due:
            return
        self.due = now + STEP
        for side in self.sides:
            self.sample(side, now)
        if now >= self.shown + 60:                                     # the state each game minute
            self.shown = now
            print(f"{recap.mmss(now)} " + "; ".join(
                f"player {s.g.player}: {train.age(s.g)}, {len(s.g.villagers)} villagers, {len(s.g.soldiers)} soldiers, "
                f"stock {' '.join(f'{r} {round(v)}' for r, v in sorted(s.g.stock.items()))}"
                + (", rung" if getattr(s, "rung", None) else "") + f", {states(s.g)}"
                for s in sorted(self.sides, key=lambda s: s.g.player)) + f"; stuck {len(self.stuck)}", file=sys.stderr)

    def sample(self, side, now):
        g = side.g
        orders = {u: (v.state, v.goal) for u, v in g.villagers.items() if v.state.startswith("to_") and v.goal}
        orders |= {u: ("attack", t) for u, t in side.targets.items() if u in g.soldiers}
        pos = {u: v.pos for u, v in g.villagers.items() if u in orders} | g.positions(sorted(orders.keys() - g.villagers.keys()))
        for u in sorted(orders.keys() - pos.keys()):                   # a dead soldier
            orders.pop(u)
        for u, order in sorted(orders.items()):
            last = self.last.get(u)
            if last is None or last[0] != order or math.dist(last[1][::2], pos[u][::2]) >= MOVED:
                self.last[u] = (order, pos[u], now)
            elif now - last[2] >= STUCK and not self.there(side, u, order, pos[u]):
                name = g.soldiers.get(u, "VILLAGER")
                self.stuck[u] = {"player": g.player, "unit": name, "order": f"{order[0]} {order[1]}",
                                 "at": [round(c, 1) for c in pos[u]], "since": recap.mmss(last[2]),
                                 "seconds": round(now - last[2])}
        self.last = {u: v for u, v in self.last.items() if u in orders or u not in g.villagers and u not in g.soldiers}   # the
                                                                       # units of the other side stay

    def there(self, side, u, order, p):
        """True when soldier u at p is in reach of its target: it fights and does not walk."""
        g = side.g
        if order[0] != "attack":
            return False
        reach = combat.stats(g.soldiers[u]).range * g.map.T + 3
        if (box := side.share.forts.get(order[1]) or g.forts.get(order[1])) is not None:
            dx = max(box[0] - p[0], 0, p[0] - box[3] - 1)
            dz = max(box[2] - p[2], 0, p[2] - box[5] - 1)
            return math.hypot(dx, dz) <= reach
        to = g.pos(order[1])
        return to is None or math.dist(to[::2], p[::2]) <= reach


def errors(path):
    """The exception lines of the server log, without the repeated ones (the same text at another time) and without
    OFFLINE: the login services that a cloud session cannot reach."""
    if not os.path.isfile(path):
        return []
    with open(path, errors="replace") as f:
        seen = {}
        for line in f:
            if ERROR.search(line) and not OFFLINE.search(line):
                seen.setdefault(TIME.sub("", line), line.rstrip())
    return list(seen.values())


def result(g, driver, watch, log):
    """The summary of the game: end, game time, ages, units, stuck units, server errors."""
    lost = vars(g).get("defeated", set())
    end = "loss" if g.player in lost else "win" if driver.foe in lost else "time"
    players = {}
    for x in (g, driver.share):
        players[x.player] = {"age": train.age(x), "ages": {a: recap.mmss(t) for a, t in sorted(vars(x).get("age_times", {}).items())},
                             "villagers": len(x.villagers), "soldiers": len(x.soldiers), "stock": dict(x.stock)}
    for side in watch.sides:                                           # the buildings of its foe that stand
        players[side.foe]["buildings"] = len(side.forts())
    bells = [f"{recap.mmss(a)}-{recap.mmss(recap.game_time(g) if b is None else b)}" for a, b in driver.bells]
    return {"end": end, "time": recap.mmss(recap.game_time(g)), "players": players, "bells": bells,
            "stuck": sorted(watch.stuck.values(), key=lambda s: (s["player"], s["since"])), "errors": errors(log)}


def play(world, speed=2.0, minutes=40.0, bot_attack="10:00", log=None, server_log=None, version=None, ai_difficulty="standard"):
    """Play the game on a copy of world; returns result()."""
    import mc_check
    import run
    out = {}
    with tempfile.TemporaryDirectory(dir=mc_check.workdir()) as tmp:
        copy = os.path.join(tmp, "PlayCheck")
        shutil.copytree(world, copy)
        run_ = gather.Gather.run

        def hooked(g, seconds=None, until=None):                   # run.play calls g.run after its setup
            foe = next(b for b in g.bots if isinstance(b, bot.Bot))
            driver = Driver(g, foe.g)
            watch = Watch(g, [foe, driver])
            g.bots = [*g.bots, driver, watch]
            out["sides"] = g, driver, watch
            return run_(g, seconds, until=lambda: recap.game_time(g) >= minutes * 60)

        with run.Game(copy, version or mc_check.DEFAULT_VERSION) as game:
            try:
                with mock.patch.object(gather.Gather, "run", hooked):
                    run.play(game, copy, log, bot=True, bot_attack=bot_attack, speed=speed, ai_difficulty=ai_difficulty)
            finally:
                path = os.path.join(game.folder, "logs", "latest.log")
                if server_log and os.path.isfile(path):
                    shutil.copyfile(path, server_log)
                if "sides" in out:
                    out["result"] = result(*out["sides"], path)
    return out["result"]


def report(r):
    lines = [f"End: {r['end']} at {r['time']} game time."]
    for p, s in sorted(r["players"].items()):
        ages = ", ".join(f"{a} {t}" for a, t in s["ages"].items()) or "none"
        lines.append(f"Player {p}: {s['age']} (ages: {ages}), {s['villagers']} villagers, {s['soldiers']} soldiers, "
                     f"{s.get('buildings', '?')} buildings, stock {s['stock']}.")
    lines.append(f"Town bell of player 1 (game time): {', '.join(r.get('bells', [])) or 'none'}.")
    lines.append(f"Stuck units: {len(r['stuck'])}.")
    lines += [f"  player {s['player']} {s['unit']} {s['order']} at {s['at']} since {s['since']} ({s['seconds']} s)"
              for s in r["stuck"]]
    lines.append(f"Server log exceptions: {len(r['errors'])}.")
    lines += [f"  {e}" for e in r["errors"][:20]]
    return "\n".join(lines)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0].strip(),
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("world", help="a converted world (aoe2mc.py) with players 1 and 2; the tool plays on a copy")
    ap.add_argument("--speed", type=float, default=2.0, help="times the Normal game speed (default 2)")
    ap.add_argument("--minutes", type=float, default=40.0, help="stop at this game time in minutes (default 40)")
    ap.add_argument("--bot-attack", default="10:00", metavar="MM:SS", help="the first attack of the bot (default 10:00)")
    ap.add_argument("--log", metavar="FILE", help="the event log of the game (run.py --log)")
    ap.add_argument("--server-log", metavar="FILE", help="copy the server log to this file")
    ap.add_argument("--json", metavar="FILE", help="write the result as JSON")
    ap.add_argument("--version", help="Minecraft version of the server")
    ap.add_argument("--ai-difficulty", default="standard", help="the AI difficulty of the bot (game/data/difficulty.jsonl)")
    a = ap.parse_args(argv)
    if not os.path.isfile(os.path.join(a.world, "level.dat")):
        sys.exit(f"no level.dat in {a.world}")
    log = open(a.log, "w") if a.log else None
    try:
        r = play(a.world, a.speed, a.minutes, a.bot_attack, log, a.server_log, a.version, a.ai_difficulty)
    finally:
        if log:
            log.close()
    if a.json:
        with open(a.json, "w") as f:
            json.dump(r, f, indent=1)
    print(report(r))
    return 0 if r["end"] != "time" and not r["stuck"] and not r["errors"] else 1


if __name__ == "__main__":
    sys.exit(main())
