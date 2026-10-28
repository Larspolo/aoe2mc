"""#2825 (epic #2538): the trigger effect "Place Foundation". The converter puts the order "found <player> <building>
<x> <y>" into the data storage aoe2mc:orders; the scenario mode of the game program puts the construction site of the
building there for free when the place is free (game/scenario.py foundation, build.found)."""
import numpy as np

import aoe2mc
from game import scenario
from test_scenario_mode import game

STORED = 'Storage aoe2mc:orders has the following contents: {list: ["found 1 HOUSE 10 12"]}'


def effect(kind="B", name="HOUSE", tile=(10, 12), player=1):
    return dict(type=aoe2mc.PLACE_FOUNDATION, message="", player=player, time=0, object=(kind, name), tile=list(tile),
                area=[-1] * 4)


def lines(*effects):
    trig = dict(id=8, name="t", enabled=True, looping=False, effects=list(effects),
                conditions=[dict(type=aoe2mc.TIMER, timer=30, inverted=False)])
    files = aoe2mc.trigger_files([trig], 4, np.full((64, 64), 70, np.int16))[1]
    return files.get("data/aoe2mc/function/trigger/8.mcfunction", "").splitlines()


def test_the_trigger_function_stores_the_order():
    assert lines(effect())[0] == 'data modify storage aoe2mc:orders list append value "found 1 HOUSE 10 12"'


def test_no_building_no_tile_or_gaia_gives_no_order():
    assert lines(effect(kind="U", name="MILITIA"), effect(tile=(-1, -1)), effect(player=0)) == []


def play(stored, blocked=()):
    server, g, bot = game({"0": {}, "1": {"color": "blue"}, "2": {"color": "red"}})
    g.map.blocked |= set(blocked)
    g.data["level_height"] = 1                                         # the design of the site (replay.Replay.draw)
    command = server.command
    server.command = lambda cmd: stored if cmd == f"data get storage {scenario.ORDERS} list" else command(cmd)
    stock = dict(g.stock)
    scenario.orders(g)
    return server, g, bot, stock


def test_a_free_place_gets_the_free_construction_site_of_the_player():
    server, g, bot, stock = play(STORED)
    assert [(s["name"], s["player"], s["footprint"]) for s in g.sites] == [("HOUSE", 1, (9, 11, 11, 13))]
    assert g.stock == stock and not bot.sites                         # free, as in AoE2; not for player 2
    assert any(c.endswith("minecraft:blue_wool") for c in server.log)  # the foundation ring in the player color
    assert f"data remove storage {scenario.ORDERS} list" in server.log


def test_a_blocked_place_gives_no_site():
    server, g, _, _ = play(STORED, blocked={(10, 12)})
    assert g.sites == [] and not any("wool" in c for c in server.log)


def test_a_bot_gets_its_site_and_a_wall_gives_none():
    _, g, bot, _ = play(STORED.replace("found 1", "found 2"))
    assert not g.sites and [s["name"] for s in bot.sites] == ["HOUSE"]
    _, g, _, _ = play(STORED.replace("HOUSE", "STONE_WALL"))
    assert g.sites == []
