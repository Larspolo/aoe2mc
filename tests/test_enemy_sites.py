"""The buildings that a side builds in the game are targets of the other side (#1819): a click of player 1 on a house
of the bot is an attack order, the bot attacks a house of player 1, and a fallen building leaves the lists."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "game"))
from test_cheat_end import game  # noqa: E402
from test_wonder import targets  # noqa: E402

from game import bot, build, combat, gather  # noqa: E402

BOT_HOUSE = {"name": "HOUSE", "player": 2, "footprint": (14, 16, 4, 6), "done": True, "progress": 1.0}
OWN_HOUSE = {"name": "HOUSE", "player": 1, "footprint": (4, 6, 14, 16), "done": True, "progress": 1.0}


def uuid(site):
    x0, x1, z0, z1 = site["footprint"]
    return combat.target_uuid([x0, z0, x1, z1])


def sides():
    server, g = game()
    b = bot.Bot(server, g.data, player=2, share=g).setup()
    g.bots = [b]
    return server, g, b


def test_a_house_that_the_bot_completes_is_a_target_of_player_1():
    server, g, b = sides()
    assert build.sides(b.g) == build.sides(g) == [g, b.g]
    build.target(b.g, BOT_HOUSE)                                     # the sites of a bot are in its own Gather
    u = uuid(BOT_HOUSE)
    assert u in g.forts and g.fort_names[u] == "HOUSE" and u not in b.g.forts
    g.selected = {"m-1"}
    eye = (3.5, 65.6, 2.5)                                           # the militia of player 1 looks at the house
    d = gather.direction(-78, 2)
    assert g.target(eye, d, {})[:2] == ("fort", u)


def test_the_bot_attacks_a_house_that_player_1_completes():
    server, g, b = sides()
    build.target(g, OWN_HOUSE)
    u = uuid(OWN_HOUSE)
    targets(server, {u})
    assert u in b.g.forts and u not in g.forts and set(b.forts()) == {u}


def test_a_fallen_building_leaves_the_lists_of_both_sides():
    server, g, b = sides()
    for site in (BOT_HOUSE, OWN_HOUSE):
        build.target(b.g if site["player"] == 2 else g, site)
    targets(server, set())                                           # both fell
    g.sieged.add(uuid(BOT_HOUSE))
    b.g.sieged.add(uuid(OWN_HOUSE))
    g.fall()
    b.g.fall()
    assert uuid(BOT_HOUSE) not in g.forts and uuid(OWN_HOUSE) not in b.g.forts and b.forts() == {}
