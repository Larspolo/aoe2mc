"""#2853 (epic #2538): the trigger effect "Set Building Gather Point". The converter puts the order "rally <player>
<ref> <x> <y>" into the data storage aoe2mc:orders; the scenario mode of the game program sets the rally point of the
building there (game/scenario.py rally, train.rally), and its new units walk to the tile."""
import types

import numpy as np

import aoe2mc
from game import gather, scenario, train
from test_gather import FakeServer, grid

BARRACKS = {"kind": "building", "name": "BARRACKS", "player": 1, "ref": 7, "footprint": [2, 2, 5, 5]}
RECT = (2, 5, 2, 5)
STORED = 'Storage aoe2mc:orders has the following contents: {list: ["rally 1 7 10 12"]}'


def effect(selected=(7,), tile=(10, 12), player=1, name="BARRACKS", area=(-1,) * 4):
    return dict(type=aoe2mc.SET_BUILDING_GATHER_POINT, message="", player=player, time=0, object=("B", name),
                tile=list(tile), area=list(area), selected=list(selected))


def lines(*effects):
    trig = dict(id=8, name="t", enabled=True, looping=False, effects=list(effects),
                conditions=[dict(type=aoe2mc.TIMER, timer=30, inverted=False)])
    files = aoe2mc.trigger_files([trig], 4, np.full((64, 64), 70, np.int16))[1]
    return files.get("data/aoe2mc/function/trigger/8.mcfunction", "").splitlines()


def test_the_trigger_function_stores_the_order_of_the_selected_barracks():
    assert lines(effect()) == ['data modify storage aoe2mc:orders list append value "rally 1 7 10 12"']


def test_no_selection_gives_one_order_for_the_type_in_the_area():
    assert lines(effect(selected=(), area=(0, 0, 8, 8))) == \
        ['data modify storage aoe2mc:orders list append value "rally 1 BARRACKS 10 12 0 0 8 8"']


def test_no_tile_gaia_or_nothing_selected_gives_no_order():
    assert lines(effect(tile=(-1, -1)), effect(player=0), effect(selected=())) == []


def play(stored, objects=(BARRACKS,)):
    server = FakeServer({})
    data = grid([[64] * 16 for _ in range(16)], [dict(o) for o in objects])
    data["players"] = {"0": {}, "1": {"color": "blue"}, "2": {"color": "red"}}
    g = gather.Gather(server, data).setup()
    bot = gather.Gather(server, data, player=2).setup()
    g.bots = [types.SimpleNamespace(g=bot)]
    command = server.command
    server.command = lambda cmd: stored if cmd == f"data get storage {scenario.ORDERS} list" else command(cmd)
    scenario.orders(g)
    server.command = command
    return server, g, bot


def test_a_new_militia_of_the_barracks_walks_to_the_tile():
    server, g, bot = play(STORED)
    assert g.rally == {RECT: ((10, 12), None)} and not bot.rally
    assert f"data remove storage {scenario.ORDERS} list" in server.log
    train.go(g, RECT, "m", "MILITIA")
    assert "aoe moveto m 10.5 64 12.5" in server.log


def test_the_area_order_and_a_bot_building():
    area = STORED.replace("rally 1 7", "rally 1 BARRACKS")
    _, g, _ = play(area.replace('12"', '12 0 0 8 8"'))
    assert g.rally == {RECT: ((10, 12), None)}
    _, g, _ = play(area.replace('12"', '12 9 9 15 15"'))
    assert not g.rally                                                 # the barracks is not in the area
    _, g, bot = play(STORED.replace("rally 1", "rally 2"), [dict(BARRACKS, player=2)])
    assert bot.rally == {RECT: ((10, 12), None)} and not g.rally


def test_a_building_that_trains_no_units_gets_no_rally_point():
    _, g, _ = play(STORED, [dict(BARRACKS, name="BLACKSMITH")])
    assert not g.rally
