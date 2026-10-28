"""The AoE2 DE setting "Ending age" of the game program (#2346, epic #2263): `game/run.py --play --end-age AGE` keeps
the ages after AGE locked. The town center menu shows the age as a gray item with the reason, and a click does
nothing."""
import pytest
from menu_line import item
from test_loom import menus, setup

from game import build, run, train


def castle(end_age=None):
    server, g = setup(food=5000, gold=5000)
    train.start(g, "castle")
    if end_age is not None:
        g.data["end_age"] = train.STARTS[end_age]["ages"]
    g.sites.append({"name": "UNIVERSITY", "player": 1, "footprint": [11, 10, 13, 12], "done": True})
    g.sites.append({"name": "MONASTERY", "player": 1, "footprint": [11, 13, 13, 15], "done": True})
    return server, g


def test_an_end_in_the_castle_age_locks_the_imperial_age():
    server, g = castle("castle")
    rect = train.open_menu(g, "Steve", (3, 3))
    assert item(menus(server)[-1], "Imperial Age").endswith("The game ends in the Castle Age")
    stock = dict(g.stock)
    assert train.order(g, "Steve", rect, train.slots("TOWN_CENTER", "IMPERIAL_AGE")[0]) == 0
    assert g.stock == stock and not g.queues.get(rect)
    assert any("Imperial Age: The game ends in the Castle Age." in c for c in server.log)


def test_the_default_is_the_game_of_today():
    for end_age in (None, "imperial"):
        server, g = castle(end_age)
        rect = train.open_menu(g, "Steve", (3, 3))
        assert item(menus(server)[-1], "Imperial Age").endswith("research")
        assert train.order(g, "Steve", rect, train.slots("TOWN_CENTER", "IMPERIAL_AGE")[0]) == 1


def test_each_end_age_locks_the_later_ages_only():
    server, g = setup()
    g.data["end_age"] = 1                                              # Feudal Age
    assert not build.locked(g, "FEUDAL_AGE") and build.locked(g, "IMPERIAL_AGE") == "The game ends in the Feudal Age"
    g.techs.add("FEUDAL_AGE")
    assert build.locked(g, "CASTLE_AGE") == "The game ends in the Feudal Age"


@pytest.mark.parametrize("start, end", [("castle", "feudal"), ("post-imperial", "castle"), ("feudal", "dark")])
def test_a_start_after_the_end_stops_with_a_message(start, end):
    with pytest.raises(SystemExit, match=f"--age {start} is after --end-age {end}"):
        run.main(["no-world", "--play", "--age", start, "--end-age", end])


def test_a_post_imperial_start_can_end_in_the_imperial_age():
    with pytest.raises(SystemExit, match="no level.dat"):              # the age check passes
        run.main(["no-world", "--play", "--age", "post-imperial", "--end-age", "imperial"])
