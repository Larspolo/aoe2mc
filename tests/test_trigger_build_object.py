"""#2863 (epic #2538): the trigger effect "Build Object". The converter puts the order "build <player> <building> <x1>
<y1> <x2> <y2>" into the data storage aoe2mc:orders; the scenario mode of the game program completes the construction
sites of the player in the area at once, with no villager work (game/scenario.py finish, build.rise)."""
from test_scenario_mode import train
from test_trigger_foundation import STORED, lines, play

import aoe2mc
from game import scenario

ORDER = 'data modify storage aoe2mc:orders list append value "build 1 {} {} {} {} {}"'


def effect(kind="B", name="HOUSE", area=(12, 14, 8, 10), player=1):
    return dict(type=aoe2mc.BUILD_OBJECT, message="", player=player, time=0, object=kind and (kind, name),
                tile=[-1, -1], area=list(area))


def test_the_trigger_function_stores_the_order_with_the_sorted_area():
    assert lines(effect()) == [ORDER.format("HOUSE", 8, 10, 12, 14)]
    assert lines(effect(kind=None, area=(-1,) * 4)) == [ORDER.format("ANY", -1, -1, -1, -1)]


def test_a_unit_type_or_gaia_gives_no_order():
    assert lines(effect(kind="U", name="MILITIA"), effect(player=0)) == []


def build(order):
    """A free construction site of a house at tile (10, 12) for player 1 (test_trigger_foundation), then the order."""
    server, g, bot, _ = play(STORED)
    site, room = g.sites[0], train.limit(g)
    command = server.command
    server.command = lambda cmd: order if cmd == f"data get storage {scenario.ORDERS} list" else command(cmd)
    server.log.clear()
    scenario.orders(g)
    return server, g, bot, site, room


def test_the_order_completes_the_site_at_once():
    server, g, _, site, room = build('{list: ["build 1 HOUSE 8 10 12 14"]}')
    assert site["done"] and site["progress"] == 1 and site["sent"] == len(site["commands"])   # all its blocks
    assert set(site["commands"]) <= set(server.log) and not any(c.endswith("_wool") for c in server.log)
    assert train.limit(g) == room + train.HOUSING["HOUSE"]             # its population space
    assert not any(v.state == "build" for v in g.villagers.values())   # no villager work


def test_another_area_type_or_player_leaves_the_site():
    for order in ("build 1 HOUSE 0 0 5 5", "build 1 MILL -1 -1 -1 -1", "build 2 ANY -1 -1 -1 -1"):
        _, g, _, site, _ = build('{list: ["%s"]}' % order)
        assert not site.get("done") and site["progress"] == 0, order
    _, g, _, site, _ = build('{list: ["build 1 ANY -1 -1 -1 -1"]}')
    assert site["done"]
