"""#3284: a text display shows the resources left above a partially drained resource (owner decision B of #3275)."""
import os
import sys
import types

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "game"))
import amounts  # noqa: E402
import gather  # noqa: E402

GOLD = next(n for n, (r, _, _) in gather.MINES.items() if r == "gold")
FULL = {"trees": gather.TREE_WOOD, "bushes": gather.BUSH_FOOD, "mines": gather.MINES[GOLD][1], "farms": 175,
        "carcasses": 100}


def side(kind):
    """A Gather with one full resource of kind on tile (2, 3), and its command list. Returns (g, amounts dict, log)."""
    m = types.SimpleNamespace(T=4, trees={}, bushes={}, mines={"gold": {}, "stone": {}}, farms={}, carcasses={},
                              farm_food=175, y=lambda x, z: 10)
    d = m.mines["gold"] if kind == "mines" else getattr(m, kind)
    d[2, 3] = FULL[kind]
    objects = [{"kind": "other", "name": GOLD, "tile": [2.0, 3.0]}] if kind == "mines" else []
    log = []
    g = types.SimpleNamespace(map=m, data={"objects": objects}, command=log.append)
    return g, d, log


@pytest.mark.parametrize("kind", ["trees", "bushes", "mines", "farms"])
def test_a_drained_resource_shows_its_amount_and_loses_it_when_empty(kind):
    g, d, log = side(kind)
    amounts.tick(g)
    assert log == ["kill @e[type=text_display,tag=aoe_left]"]          # full: no display
    log.clear()
    d[2, 3] -= 1.5                                                     # one take
    amounts.tick(g)
    n = FULL[kind] - 2
    assert log == [f"kill @e[type=text_display,tag=aoe_left.{kind}.2.3]",
                   f'summon text_display 10.5 {10 + amounts.HIGH[kind]} 14.5 {{text:"{n}",billboard:"center",'
                   f'Tags:["aoe_left","aoe_left.{kind}.2.3"]}}']
    log.clear()
    amounts.tick(g)
    assert log == []                                                   # no change: no command
    d[2, 3] -= 1
    amounts.tick(g)
    assert log == [f'data merge entity @e[type=text_display,tag=aoe_left.{kind}.2.3,limit=1] {{text:"{n - 1}"}}']
    log.clear()
    d[2, 3] = 0
    amounts.tick(g)
    assert log == [f"kill @e[type=text_display,tag=aoe_left.{kind}.2.3]"]


def test_a_tree_shows_99_after_one_wood():
    g, d, log = side("trees")
    d[2, 3] = 99
    amounts.tick(g)
    assert 'text:"99"' in log[-1]


def test_a_carcass_shows_from_the_kill_as_it_rots():
    g, d, log = side("carcasses")
    amounts.tick(g)
    assert 'text:"100"' in log[-1]
    del d[2, 3]                                                        # all food taken: the map drops the tile
    log.clear()
    amounts.tick(g)
    assert log == ["kill @e[type=text_display,tag=aoe_left.carcasses.2.3]"]


def test_a_bot_and_a_bare_gather_show_nothing():
    g, d, log = side("trees")
    d[2, 3] = 50
    g.share = object()                                                 # bot.py: the Gather of a bot
    amounts.tick(g)
    amounts.tick(object.__new__(gather.Gather))                        # tests/test_play_speed.py
    assert log == []
