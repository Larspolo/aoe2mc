"""Live replay: a garrisoned unit adds its arrow to its town center, as in the game program (#1203, #1113). Fake RCON."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "game"))
import garrison  # noqa: E402
from test_replay_garrison import TC, order, play, ungarrison  # noqa: E402

from game import combat  # noqa: E402

UUID = combat.target_uuid(TC["footprint"])


def arrows(sent):
    return [c for c in sent if c.startswith("aoe arrows ")]


def test_two_villagers_inside_give_their_arrows_and_ungarrison_takes_them_away():
    _, sent = play([order(0, [7, 8], 50), ungarrison(20000)], 30000, ai=True)
    two = garrison.arrows("TOWN_CENTER", ["VILLAGER_MALE"] * 2)
    assert two == 2 and garrison.arrows("TOWN_CENTER", []) == 0         # an empty town center shoots no arrow (#1201)
    assert arrows(sent) == [f"aoe arrows {UUID} 1", f"aoe arrows {UUID} {two}", f"aoe arrows {UUID} 0"]   # one by one
    assert sent.index(f"aoe arrows {UUID} 0") > sent.index("tag u1 remove aoe2mc.garrisoned")


def test_without_the_plugin_no_arrows():
    _, sent = play([order(0, [7, 8], 50), ungarrison(20000)], 30000, ai=False)
    assert arrows(sent) == []
