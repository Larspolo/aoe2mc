"""
The AoE2 DE order "Auto Scout" (#3702, epic #3701 item 1): a scout walks to the nearest tile that its side did not
explore (g.explored, score.explore), then to the next one, until a new order or until the side explored the whole map.
The live replay has the same choice (replay.Replay.scout_on, #2678).
g.scouting: scout UUID -> [goal tile or None, last feet tile or None, set of tried tiles].
"""
import math

import numpy as np


def start(g, units):
    """Give the units the Auto Scout order: the next tick walks them."""
    units = sorted(units)
    if not units:
        return
    g.new_order(units)                                             # it ends the old scouting of the units too
    scouting = vars(g).setdefault("scouting", {})
    for u in units:
        scouting[u] = [None, None, set()]
    tick(g)


def end(g, units):
    """A new order ends the scouting of the units."""
    scouting = vars(g).get("scouting", {})
    for u in set(units) & scouting.keys():
        del scouting[u]


def nearest(g, p, tried):
    """The nearest tile to the feet position p that the side did not explore and that the scout did not try, or None."""
    T = g.map.T
    n = g.data.get("map_size") or g.map.n // T
    free = np.ones((n, n), bool)
    old = [(x, y) for x, y in vars(g).get("explored", set()) | tried if 0 <= x < n and 0 <= y < n]
    if old:
        free[tuple(np.array(old).T)] = False
    if not free.any():
        return None
    xs, ys = np.nonzero(free)
    k = np.argmin((xs + 0.5 - p[0] / T) ** 2 + (ys + 0.5 - p[2] / T) ** 2)
    return int(xs[k]), int(ys[k])


def tick(g):
    """Walk each scout that stands (on its goal, or on the same tile as at the last tick) or has no goal to the
    nearest unexplored tile. A dead scout, or a side that explored all tiles, ends the entry."""
    scouting = vars(g).get("scouting")
    if not scouting:
        return
    pos = g.positions(sorted(scouting))
    T = g.map.T
    for u, entry in sorted(scouting.items()):
        goal, last, tried = entry
        if (p := pos.get(u)) is None:
            del scouting[u]
            continue
        here = (math.floor(p[0] / T), math.floor(p[2] / T))
        tried.add(here)                                            # its own tile: no walk of length 0
        entry[1] = here
        if goal is not None and goal != here and here != last:
            continue                                               # it still walks
        if (goal := nearest(g, p, tried)) is None:
            del scouting[u]
            continue
        tried.add(goal)                                            # a tile out of reach stays unexplored
        entry[0] = goal
        x, z = goal[0] * T + T // 2, goal[1] * T + T // 2
        g.command(f"aoe moveto {u} {x} {g.map.y(x, z)} {z}")
