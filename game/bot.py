"""A bot plays a player of the game program without a human (#397). First step (#856): its villagers gather food,
wood, gold and stone.

The bot has its own gather.Gather for its player. That Gather gets no clicks, and it writes its resources to its own
objective (Gather.board), which no sidebar shows: the sidebar of player 1 does not change. Each step sends the idle
villagers to the nearest source of the resource with the largest gap to SHARE. The villagers walk with the plugin
(`aoe moveto`) on Paper, as the villagers of player 1.
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gather  # noqa: E402

SHARE = {"food": 0.4, "wood": 0.3, "gold": 0.2, "stone": 0.1}     # the villagers on each resource (a simple AoE2 bot)


class Bot:
    def __init__(self, game, data, player=2, share=None, **kw):
        """share: the Gather of the human player. Both then use the same trees, bushes and mines."""
        self.g = gather.Gather(game, data, player=player, **kw)
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
