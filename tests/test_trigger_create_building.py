"""#2911 (epic #2538): the trigger effect "Create Object" of a building. The converter puts the order "create <player>
<building> <x> <y>" into the data storage aoe2mc:orders; the scenario mode of the game program puts the complete
building there when the place is free (game/scenario.py foundation with done, build.rise)."""
import numpy as np
from test_trigger_foundation import play

import aoe2mc

STORED = 'Storage aoe2mc:orders has the following contents: {list: ["create 1 HOUSE 10 12"]}'


def lines(kind="B", name="HOUSE", player=1):
    e = dict(type=aoe2mc.CREATE_OBJECT, message="", player=player, time=0, object=(kind, name), tile=[10, 12],
             area=[-1] * 4)
    trig = dict(id=8, name="t", enabled=True, looping=False, effects=[e],
                conditions=[dict(type=aoe2mc.TIMER, timer=30, inverted=False)])
    files = aoe2mc.trigger_files([trig], 4, np.full((64, 64), 70, np.int16))[1]
    return files.get("data/aoe2mc/function/trigger/8.mcfunction", "").splitlines()


def test_a_building_gives_the_order_and_a_unit_the_summon():
    assert lines()[0] == 'data modify storage aoe2mc:orders list append value "create 1 HOUSE 10 12"'
    assert lines("U", "MILITIA")[0].startswith("summon ")


def test_a_free_place_gets_the_complete_building():
    server, g, bot, stock = play(STORED)
    assert [(s["name"], s["player"], bool(s.get("done"))) for s in g.sites] == [("HOUSE", 1, True)]
    assert g.stock == stock and not bot.sites


def test_a_blocked_place_gives_no_building():
    server, g, _, _ = play(STORED, blocked={(10, 12)})
    assert g.sites == [] and not any("wool" in c for c in server.log)
