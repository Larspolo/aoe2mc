"""A bot plays a player of the game program without a human (#397). First step (#856): its villagers gather food,
wood, gold and stone. It trains villagers up to a number, then soldiers at its military buildings (#858).

The bot has its own gather.Gather for its player. That Gather gets no clicks, and it writes its resources to its own
objective (Gather.board), which no sidebar shows: the sidebar of player 1 does not change. Each step sends the idle
villagers to the nearest source of the resource with the largest gap to SHARE. The villagers walk with the plugin
(`aoe moveto`) on Paper, as the villagers of player 1.

Build (#857): a house when the population is 2 below the limit, then the buildings of ORDER when the bot has their
cost. One villager builds each site (an idle one, else the nearest), next to the source of the building (NEAR) or
the town center. An unfinished site without a working builder gets a new one (#1121). Each building of ORDER once, as the first buildings of an AoE2 build order.

Army shares (#1049): when the bot has its villager number and a building that trains a soldier, the shares follow the
cost of that soldier (train.COSTS), with WOOD for farms and houses; stone gets no new villagers. Each step moves at
most one working villager from a resource above its share to the resource most below its share, as an AoE2 bot does.

Attack (#859): until the game time `attack` (AoE2 seconds) the soldiers stay at their buildings. Then each soldier
without a live target attacks the nearest unit of player `foe`, else its nearest building, with the mob AI of the
plugin (`ai.attack`, `aoe attack`). A soldier gets a new target when its target dies.

Difficulty (#2661, decision #2648): the AoE2 DE setting "AI difficulty" (run.py --ai-difficulty) is one line of
game/data/difficulty.jsonl (LEVELS): "gather" times the work rate of the bot villagers, "attack" times the time of the
first attack, "soldiers" in the first wave. AoE2 does not publish what each level changes: the values are a guess.
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ai  # noqa: E402
import build  # noqa: E402
import combat  # noqa: E402
import gather  # noqa: E402
import herd  # noqa: E402
import table  # noqa: E402
import train  # noqa: E402

SHARE = {"food": 0.4, "wood": 0.3, "gold": 0.2, "stone": 0.1}     # the villagers on each resource (a simple AoE2 bot)
WOOD = 0.2                                                         # the wood share for farms and houses with an army
QUEUED = 2                                                         # units in the queue of each building of the bot
# The build order after the houses (the key "bot" of data/build.jsonl), and the resource that a drop site goes next to
ORDER = tuple(r["name"] for r in sorted((r for r in build.ROWS if "bot" in r), key=lambda r: r["bot"]))
NEAR = {r["name"]: r["near"] for r in build.ROWS if "near" in r}
HOUSE_GAP = 2                                                      # a new house at this many units below the limit
ATTACK = 600.0                                                     # AoE2 seconds: the first attack at 10:00
LOOK = 2.0                                                         # AoE2 seconds between two looks for targets
LEVELS = {r["name"]: r for r in table.load("difficulty.jsonl")}    # "AI difficulty", in the order of the AoE2 lobby


class Bot:
    def __init__(self, game, data, player=2, share=None, villagers=20, attack=ATTACK, foe=1, group=None,
                 difficulty="standard", **kw):
        """share: the Gather of the human player. Both then use the same trees, bushes and mines.
        villagers: the bot trains villagers up to this number, then soldiers.
        attack: the game time (AoE2 seconds) of the first attack on player foe, times the "attack" of the difficulty.
        group: the soldiers of the first wave (default: the "soldiers" of the difficulty); until then they stay at
        their buildings (#1051). difficulty: a name of LEVELS (#2661)."""
        level = LEVELS[difficulty]
        self.g = gather.Gather(game, data, player=player, **kw)
        self.g.chop = {k: s / level["gather"] for k, s in self.g.chop.items()}   # seconds per unit: work_time
        self.villagers, self.attack, self.foe, self.share = villagers, attack * level["attack"], foe, share
        self.group = level["soldiers"] if group is None else group
        self.charged = False                                           # the wave attacks: new soldiers join it
        self.time, self.looked, self.targets = 0.0, -LOOK, {}          # AoE2 seconds of the game, soldier -> target
        self.nobody = f"@a[tag=aoe2mc.bot{player}]"                     # the texts of the queues go to no player
        self.g.share = share                                           # monk.heresy: the techs of the human player
        if share:
            self.g.map.trees, self.g.map.bushes, self.g.map.mines = share.map.trees, share.map.bushes, share.map.mines
            self.g.relics = share.relics                                # one list: each relic exists once (#3116)
        self.failed = set()                                            # sources that a villager could not reach
        self.sides = (None, {})                                        # (own and foe places, {tile: at home}) (#1810)
        self.g.home = self.home                                        # the next bush or mine of Gather.nearest too

    def setup(self):
        """Find the villagers of the player (the entities must be loaded) and make the objective of the resources."""
        g = self.g
        g.command(f'scoreboard objectives add {g.board} dummy "Player {g.player}"')
        g.show_stock()                                                 # spending and gathering add to these (#2833)
        for o in g.units:
            if pos := g.pos(o["uuid"]):
                g.villagers[o["uuid"]] = gather.Villager(o["uuid"], pos)
        return self

    def sources(self, res):
        """{tile: amount} of the trees, the fruit bushes and the own farms without a farmer, or the mines of res."""
        m = self.g.map
        if res == "food":                                              # a farm takes one farmer (Gather.send)
            return self.home({**m.bushes, **{t: k for t, k in m.farms.items() if t in m.own_farms and t not in self.g.farmers}})
        return self.home(m.trees if res == "wood" else m.mines[res])

    def home(self, sources):
        """The sources {tile: amount} whose tile is not nearer to a building of the foe than to an own town center or
        drop site (#1810): an AoE2 AI gathers at its own base. Else the bot sent its villagers to the bushes next to the
        town center of the foe when its own ones were empty, and they died there; now it builds farms (build)."""
        g, T = self.g, self.g.map.T
        own = tuple(sorted((sum(x for x, _ in c) / len(c), sum(z for _, z in c) / len(c))
                           for r in sorted(g.map.drops) for c in g.map.drops[r] if c))
        foe = tuple(sorted({((x0 + x1) / 2, (z0 + z1) / 2) for o in g.data["objects"] if o["kind"] == "building"
                            and o["player"] == self.foe and "footprint" in o for x0, z0, x1, z1 in [o["footprint"]]} |
                           {((x0 + x1) / 2, (z0 + z1) / 2) for s in (self.share.sites if self.share else ())
                            if s["player"] == self.foe for x0, x1, z0, z1 in [s["footprint"]]}))
        if not own or not foe:
            return sources
        if self.sides[0] != (own, foe):                                # a new building: decide each tile again
            self.sides = ((own, foe), {})
        at = self.sides[1]
        for t in sources.keys() - at.keys():
            c = ((t[0] + 0.5) * T, (t[1] + 0.5) * T)
            at[t] = min(math.dist(c, p) for p in own) <= min(math.dist(c, p) for p in foe)
        return {t: k for t, k in sources.items() if at[t]}

    def step(self):
        """One tick of the gather game of the player, then orders for the idle villagers."""
        g = self.g
        g.step()
        self.build()
        share = self.shares()
        work = {r: 0 for r in SHARE}
        idle = []
        for v in g.villagers.values():
            if v.state != "idle":
                work[v.res] += 1
            elif v.tree is not None and self.sources(v.res).get(v.tree, 0) > 0:
                self.failed.add(v.tree)                                # idle next to a full source: no path
                v.tree = None
                idle.append(v)
            else:
                idle.append(v)
        n = len(g.villagers)
        for v in sorted(idle, key=lambda v: v.uuid):
            for res in sorted(SHARE, key=lambda r: (work[r] - share[r] * n, r)):     # the largest gap first
                if self.go(v, res):
                    work[res] += 1
                    break
        self.move(share, work)
        self.recruit()
        self.time += g.tick * gather.NORMAL
        if self.time >= self.attack and self.time >= self.looked + LOOK:   # each look costs RCON commands
            self.looked = self.time
            self.fight()

    def go(self, v, res):
        """Send villager v to the nearest source of res that has some left. False when there is none."""
        g = self.g
        full = [t for t, k in self.sources(res).items() if k > 0 and t not in self.failed]
        if full:
            T = g.map.T
            g.send(min(full, key=lambda t: (math.dist(v.cell, ((t[0] + 0.5) * T, (t[1] + 0.5) * T)), t)), {v.uuid})
        return bool(full)

    def army(self):
        """The military unit that the first own training building (not a town center) trains, or None."""
        g = self.g
        return next((n for rect, name in sorted(train.homes(self.g).items()) if name != "TOWN_CENTER"
                     for n in train.trains(g, name) if gather.military(n) and n not in train.TECHS
                     and not build.locked(g, n)), None)

    def shares(self):
        """SHARE, or the shares of the army (#1049) when the bot has its villager number and trains a soldier."""
        unit = len(self.g.villagers) >= self.villagers and self.army()
        if not unit:
            return SHARE
        cost = train.price(self.g, unit)
        total = sum(cost.values())
        return {r: (WOOD if r == "wood" else 0) + (1 - WOOD) * cost.get(r, 0) / total for r in SHARE}

    def move(self, share, work):
        """Move one working villager from the resource most above its share to the resource most below it, when the
        first has a whole villager too many: then the move never goes back. Food with no free farm: to wood, the cost
        of the next farm (#1083)."""
        g, n = self.g, len(self.g.villagers)
        gap = {r: work[r] - share[r] * n for r in SHARE}
        low = min(SHARE, key=lambda r: (gap[r], r))
        if gap[low] >= 0:
            return
        if low == "food" and not any(k > 0 for k in self.sources("food").values()):
            low = "wood"
        high = max((r for r in SHARE if r != low), key=lambda r: (gap[r], r))
        if gap[high] < 1:
            return
        busy = sorted(u for u, v in g.villagers.items() if v.state != "idle" and v.res == high and v.site is None)
        for v in [g.villagers[u] for u in busy[:1]]:                   # a builder stays at its site
            if self.go(v, low):
                work[high] -= 1
                work[low] += 1

    def fight(self):
        """Send each soldier without a live target to the nearest unit of the foe in reach and in the sight of the bot
        (#2050), else to its nearest building. A wave starts with self.group soldiers; when all of it is dead, the next wave waits for a full group again (#1051)."""
        g = self.g
        mine = g.positions(sorted(g.soldiers))                         # a dead soldier is not in it
        self.charged = len(mine) >= self.group or self.charged and bool(mine)
        if not self.charged:
            return
        live = {t for t in set(self.targets.values()) if "passed" in g.command(f"execute if entity {t}")}
        self.targets = {u: t for u, t in self.targets.items() if u in mine and t in live}
        if not mine.keys() - {u for u, t in self.targets.items() if t not in g.forts}:
            return                                                     # all soldiers fight units
        units = {o["uuid"] for o in g.data["objects"] if o["kind"] == "unit" and o["player"] == self.foe and o.get("uuid")
                 and not herd.herdable(o["name"])}                     # AoE2: a sheep is captured, not attacked (#2049)
        if self.share:                                                 # also the units that player 1 trained
            units |= self.share.villagers.keys() | self.share.soldiers.keys()
        seen, T = g.seen_tiles(), g.map.T                              # the AoE2 AI sees only its sight (#2050)
        near = {k: p for k, p in g.positions(sorted(units)).items() if (int(p[0] // T), int(p[2] // T)) in seen}
        self.targets = {u: t for u, t in self.targets.items()          # a unit that comes in sight goes before a
                        if t not in g.forts or not any(self.reach(u, mine[u], p) for p in near.values())}   # building
        free = sorted(mine.keys() - self.targets.keys())
        forts, orders = None, {}
        for u in free:
            ok = {k: p for k, p in near.items() if self.reach(u, mine[u], p)}
            if not ok:                                                 # no unit in reach, for example only a ship on
                if forts is None:                                      # the water: the buildings, as in AoE2 (#1770)
                    forts = {t: ((b[0] + b[3] + 1) / 2, b[1], (b[2] + b[5] + 1) / 2) for t, b in self.forts().items()}
                ok = {k: p for k, p in forts.items() if self.reach(u, mine[u], p)}
            if not ok:
                continue
            t = min(ok, key=lambda k: (math.dist(ok[k], mine[u]), k))
            self.targets[u] = t
            orders.setdefault(t, []).append(u)
        for t, us in sorted(orders.items()):
            if t in g.forts:
                g.sieged.add(t)                                        # Gather.fall frees its footprint
            ai.attack(g.game, us, [g.soldiers[u] for u in us], g.map.T, t,
                      [gather.NORMAL * train.speed(g, g.soldiers[u], u) for u in us])

    def reach(self, u, at, to):
        """True when soldier u at `at` can attack a target at `to`. AoE2: a land unit cannot walk to a ship on the water
        (#1658): it attacks a target on a water cell only with its range, from the land. A ship attacks all."""
        wet = self.g.map.y(math.floor(to[0]), math.floor(to[2])) is None
        if not wet or self.g.map.y(math.floor(at[0]), math.floor(at[2])) is None:
            return True
        return math.dist(at[::2], to[::2]) <= combat.stats(self.g.soldiers[u]).range * self.g.map.T

    def forts(self):
        """{target UUID: box} of the buildings of the foe whose target entity lives: those of the map and those that
        the foe built in the game (build.target, #1819)."""
        g = self.g
        return {u: box for u, box in sorted(g.forts.items()) if g.fort_players.get(u) == self.foe
                and "passed" in g.command(f"execute if entity {u}")}

    def recruit(self):
        """Keep QUEUED units in the queue of each training building: villagers at the town centers up to
        self.villagers, and the first military unit of the age at the other buildings, when the resources are there.
        A town center comes first: the villagers get the resources first."""
        g = self.g
        for rect, name in sorted(train.homes(g).items(), key=lambda kv: (kv[1] != "TOWN_CENTER", kv[0])):
            more = len(g.villagers) + sum(e["name"] == "VILLAGER_MALE" for q in g.queues.values() for e in q)
            units = ["VILLAGER_MALE"] if name == "TOWN_CENTER" else \
                [n for n in train.trains(g, name) if gather.military(n) and n not in train.TECHS and not build.locked(g, n)]
            for n in units[:1]:
                while len(g.queues.get(rect, [])) < QUEUED and (n != "VILLAGER_MALE" or more < self.villagers) \
                        and all(g.stock[r] >= v for r, v in train.price(g, n).items()) \
                        and train.queue(g, self.nobody, (rect[0], rect[2]), n):
                    more += n == "VILLAGER_MALE"

    def build(self):
        """Start the next house, farm or building of ORDER when the bot can pay for it and no site of it is unfinished.
        A farm when no food source is left at its base (#1026, #1810), at most one for each food villager of the shares."""
        g = self.g
        if open_ := [s for s in g.sites if not s.get("done")]:           # one site at a time
            for site in open_:                                         # its builder left or died (#1121)
                if g.villagers and not any(v.site is site and v.state != "idle" for v in g.villagers.values()):
                    self.builder(site)
            return
        cap, have = train.limit(g), train.owned(g)
        farms = sum(k > 0 for t, k in g.map.farms.items() if t in g.map.own_farms)
        hungry = not any(k > 0 for k in self.sources("food").values()) and farms < math.ceil(self.shares()["food"] * len(g.villagers))
        name = "HOUSE" if g.pop >= cap - HOUSE_GAP and cap < train.max_pop(g) else "FARM" if hungry else \
            next((n for n in ORDER if n not in have), None)
        if name is None or any(g.stock[r] < v for r, v in build.price(g, name).items()):
            return
        center = self.center()
        if (res := NEAR.get(name)) and (full := [t for t, k in self.sources(res).items() if k > 0]):
            T = g.map.T
            center = min(((t[0] * T + T // 2, t[1] * T + T // 2) for t in full), key=lambda c: (math.dist(c, center), c))
        if center is None or (rect := build.near(g, name, center)) is None or not g.villagers:
            return
        self.builder(build.found(g, name, rect))

    def builder(self, site):
        """Send one villager to build site: an idle one, else the nearest."""
        g = self.g
        x0, x1, z0, z1 = site["footprint"]
        x, z = (x0 + x1) / 2, (z0 + z1) / 2
        v = min(g.villagers.values(), key=lambda v: (v.state != "idle", math.dist(v.cell, (x, z)), v.uuid))
        g.build(site, {v.uuid})

    def center(self):
        """The middle block cell of the first own town center, or None."""
        tc = next((o["footprint"] for o in self.g.data["objects"] if o["kind"] == "building"
                   and o["player"] == self.g.player and o["name"] == "TOWN_CENTER"), None)
        return tc and ((tc[0] + tc[2]) // 2, (tc[1] + tc[3]) // 2)
