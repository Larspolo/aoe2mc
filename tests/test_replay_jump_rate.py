"""A long jump gathers at the AoE2 rate for the whole skipped time, not only what one resource has (#1147)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gather  # noqa: E402
import replay  # noqa: E402
from test_replay import data  # noqa: E402
from test_replay_control import Clock  # noqa: E402
from test_replay_gather import MINE, TREE, VIL  # noqa: E402

MINUTES = 43 * 60 * 1000                                           # the jump of check #1087 (ms)


def jump(obj, t0=0, t1=MINUTES):
    """Replay with one villager at the resource `obj`; the estimate and the summary of player 1 after skipped()."""
    d = data([])
    d["objects"] += [VIL, obj]
    r = replay.Replay(Clock(), d)
    r.grid()
    r.units[7].tree = int(obj["tile"][0]), int(obj["tile"][1])        # the tile of the resource in gather.Map
    r.skipped(7, t0, t1)
    return r.resources(1), r.gathered.get(1, {})


def test_a_long_jump_gathers_more_than_one_tree():
    stock, got = jump(TREE)
    assert got["wood"] == int(gather.AOE2_WORK["wood"] * MINUTES / 1000) > gather.TREE_WOOD
    assert stock["wood"] == replay.START["wood"] + got["wood"]


def test_a_long_jump_gathers_more_than_one_mine():
    stock, got = jump(MINE)
    assert got["stone"] == int(gather.AOE2_WORK["stone"] * MINUTES / 1000) > gather.MINES["STONE_MINE"][1]
    assert stock["stone"] == replay.START["stone"] + got["stone"]


def test_a_short_jump_keeps_the_rate():
    _, got = jump(TREE, 0, 10000)
    assert got["wood"] == int(gather.AOE2_WORK["wood"] * 10)
