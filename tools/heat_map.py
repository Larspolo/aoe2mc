"""Write the walk heat map of the record of a converted world as a PNG (#5455): the target tiles of the moves and
orders of each player in its color.

Usage: python3 tools/heat_map.py WORLD OUT.png [--kind walk] [--from MM:SS] [--to MM:SS]
"""
import argparse
import json
import math
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path[:0] = [os.path.join(ROOT, "game"), ROOT]

import heatmap  # noqa: E402
import replay  # noqa: E402

import aoe2mc  # noqa: E402


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("world")
    ap.add_argument("out")
    ap.add_argument("--kind", default="walk", choices=["walk"])
    ap.add_argument("--from", dest="start", default="0:00")
    ap.add_argument("--to", dest="end")
    a = ap.parse_args(argv)
    with open(os.path.join(a.world, "aoe2mc.json")) as f:
        data = json.load(f)
    if "timeline" not in data:
        sys.exit("the world has no record (convert a .aoe2record)")
    events = data["timeline"]
    end = aoe2mc.game_time(a.end) if a.end else math.inf
    grids = heatmap.grid(events, replay.owners(data["objects"], events), data["map_size"], a.kind,
                         aoe2mc.game_time(a.start), end)
    heatmap.image(grids, heatmap.colors(data["players"])).save(a.out)
    print(f"{a.out}: {', '.join(f'player {p}: {int(g.sum())}' for p, g in sorted(grids.items())) or 'no events'}")


if __name__ == "__main__":
    main()
