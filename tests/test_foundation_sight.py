"""A construction site gives no line of sight until it is complete (#4176)."""
import os
import sys
import types

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "game"))
import combat  # noqa: E402
import gather  # noqa: E402

T = 4


def bare(progress):
    g = gather.Gather.__new__(gather.Gather)
    g.player, g.data, g.map = 1, {"objects": []}, types.SimpleNamespace(T=T)
    g.villagers, g.soldiers = {}, {}
    g.sites = [{"name": "HOUSE", "player": 1, "footprint": (10 * T, 12 * T, 70 * T, 72 * T), "progress": progress}]
    return g


def test_a_site_sees_only_when_complete():
    for k in (0.0, 0.5, 0.99):
        assert bare(k).seen_tiles({}) == set()
    assert (11, 70 + combat.sight("HOUSE")) in bare(1.0).seen_tiles({})
