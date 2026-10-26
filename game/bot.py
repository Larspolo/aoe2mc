"""A bot plays a player of the game program without a human (#397). First step (#856): its villagers gather food,
wood, gold and stone. It trains villagers up to a number, then soldiers at its military buildings (#858).

The bot has its own gather.Gather for its player. That Gather gets no clicks, and it writes its resources to its own
objective (Gather.board), which no sidebar shows: the sidebar of player 1 does not change. Each step sends the idle
villagers to the nearest source of the resource with the largest gap to SHARE. The villagers walk with the plugin
(`aoe moveto`) on Paper, as the villagers of player 1.

Build (#857): a house when the population is 2 below the limit, then the buildings of ORDER when the bot has their
cost. One villager builds each site (an idle one, else the nearest), next to the source of the building (NEAR) or
the town center. Each building of ORDER once, as the first buildings of an AoE2 build order.
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build  # noqa: E402
import gather  # noqa: E402
import train  # noqa: E402

SHARE = {"food": 0.4, "wood": 0.3, "gold": 0.2, "stone": 0.1}     # the villagers on each resource (a simple AoE2 bot)
QUEUED = 2                                                         # units in the queue of each building of the bot
ORDER = ("LUMBER_CAMP", "MILL", "MINING_CAMP", "BARRACKS")         # the build order after the houses
NEAR = {"LUMBER_CAMP": "wood", "MILL": "food", "MINING_CAMP": "gold"}   # a drop site goes next to its resource
HOUSE_GAP = 2                                                      # a new house at this many units below the limit


class Bot:
    def __init__(self, game, data, player=2, share=None, villagers=20, **kw):
        """share: the Gather of the human player. Both then use the same trees, bushes and mines.
        villagers: the bot trains villagers up to this number, then soldiers."""
        self.g = gather.Gather(game, data, player=player, **kw)
        self.villagers = villagers
        self.nobody = f"@a[tag=aoe2mc.bot{player}]"                     # the texts of the queues go to no player
        if share:
            self.g.map.trees, self.g.map.bushes, self.g.map.mines = share.map.trees, share.map.bushes, share.map.mines
        self.g.board = f"aoe_bot{player}"                              # not aoe_res: the sidebar of player 1
        self.failed = set()                                            # sources that a villager could not reach

    def setup(self):
        """Find the villagers of the player (the entities must be loaded) and make the objective of the resources."""
        g = self.g
        g.command(f'scoreboard objectives add {g.board} dummy "Player {g.player}"')
        for o in g.units:
            if pos := g.pos(o["uuid"]):
                g.villagers[o["uuid"]] = gather.Villager(o["uuid"], pos)
        return self

    def sources(self, res):
        """{tile: amount} of the trees, fruit bushes or mines of res."""
        m = self.g.map
        return m.trees if res == "wood" else m.bushes if res == "food" else m.mines[res]

    def step(self):
        """One tick of the gather game of the player, then orders for the idle villagers."""
        g = self.g
        g.step()
        self.build()
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
            for res in sorted(SHARE, key=lambda r: (work[r] - SHARE[r] * n, r)):     # the largest gap first
                full = [t for t, k in self.sources(res).items() if k > 0 and t not in self.failed]
                if full:
                    T = g.map.T
                    tile = min(full, key=lambda t: (math.dist(v.cell, ((t[0] + 0.5) * T, (t[1] + 0.5) * T)), t))
                    g.send(tile, {v.uuid})
                    work[res] += 1
                    break
        self.recruit()

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
                        and all(g.stock[r] >= v for r, v in train.COSTS[n].items()) \
                        and train.queue(g, self.nobody, (rect[0], rect[2]), n):
                    more += n == "VILLAGER_MALE"

    def build(self):
        """Start the next house or building of ORDER when the bot can pay for it and no site of it is unfinished."""
        g = self.g
        if any(not s.get("done") for s in g.sites):                    # one site at a time
            return
        cap, have = train.limit(g), train.owned(g)
        name = "HOUSE" if g.pop >= cap - HOUSE_GAP and cap < train.LIMIT else \
            next((n for n in ORDER if n not in have), None)
        if name is None or any(g.stock[r] < v for r, v in build.COSTS[name].items()):
            return
        center = self.center()
        if (res := NEAR.get(name)) and (full := [t for t, k in self.sources(res).items() if k > 0]):
            T = g.map.T
            center = min(((t[0] * T + T // 2, t[1] * T + T // 2) for t in full), key=lambda c: (math.dist(c, center), c))
        if center is None or (rect := build.near(g, name, center)) is None or not g.villagers:
            return
        site = build.found(g, name, rect)
        x, z = (rect[0] + rect[1]) / 2, (rect[2] + rect[3]) / 2
        v = min(g.villagers.values(), key=lambda v: (v.state != "idle", math.dist(v.cell, (x, z)), v.uuid))
        g.build(site, {v.uuid})

    def center(self):
        """The middle block cell of the first own town center, or None."""
        tc = next((o["footprint"] for o in self.g.data["objects"] if o["kind"] == "building"
                   and o["player"] == self.g.player and o["name"] == "TOWN_CENTER"), None)
        return tc and ((tc[0] + tc[2]) // 2, (tc[1] + tc[3]) // 2)
