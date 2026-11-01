"""The fight heat map of a record (#5456)."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "game"))
import heatmap  # noqa: E402

OWNER = {10: 2, 11: 1, 12: 0}


def count(e):
    g = heatmap.grid([dict(e, time=0, tile=[3, 4])], OWNER, 8, kind="fight")
    return sum(int(a[3, 4]) for a in g.values())


def test_attack_orders_count():
    assert count({"kind": "order", "player": 1, "target": 10}) == 1
    assert count({"kind": "attack_move", "player": 1}) == 1


def test_other_orders_do_not_count():
    assert count({"kind": "order", "player": 1, "target": 11}) == 0      # own unit
    assert count({"kind": "order", "player": 1, "target": 12}) == 0      # Gaia
    assert count({"kind": "move", "player": 1}) == 0


def test_player_of_the_count():
    g = heatmap.grid([{"kind": "order", "player": 2, "target": 11, "time": 0, "tile": [1, 1]}], OWNER, 4, kind="fight")
    assert list(g) == [2] and g[2][1, 1] == 1
