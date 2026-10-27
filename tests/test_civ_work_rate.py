"""game/civs.py: Persian town centers and docks train and research 5/10/15/20 % faster in the Dark/Feudal/Castle/Imperial
Age (AoE2 DE wiki, "Persians", #1894); other buildings and civilizations keep the AoE2 times."""
import pytest
from test_forging import menus, setup

from game import train

TC, BARRACKS = (2, 5, 2, 5), (16, 19, 2, 5)
AGES = ("FEUDAL_AGE", "CASTLE_AGE", "IMPERIAL_AGE")


def game(civ, age=0):
    server, g = setup(age=0)
    g.data["players"] = {"1": {"civ": civ}}
    g.techs.update(AGES[:age])
    return server, g


@pytest.mark.parametrize("age, factor", [(0, 1.05), (1, 1.1), (2, 1.15), (3, 1.2)])
def test_a_persian_villager_trains_faster_in_each_age(age, factor):
    _, g = game("PERSIANS", age)
    assert train.seconds(g, "VILLAGER_MALE", "TOWN_CENTER") == pytest.approx(25 / factor)
    assert train.seconds(g, "FISHING_SHIP", "DOCK") == pytest.approx(train.TRAIN_TIMES["FISHING_SHIP"] / factor)


def test_the_feudal_age_research_is_faster_and_a_briton_villager_is_not():
    _, g = game("PERSIANS")
    assert train.seconds(g, "FEUDAL_AGE", "TOWN_CENTER") == pytest.approx(130 / 1.05)
    _, g = game("BRITONS", 3)
    assert train.seconds(g, "VILLAGER_MALE", "TOWN_CENTER") == 25


def test_the_queue_of_the_town_center_ends_sooner_and_the_barracks_not():
    _, g = game("PERSIANS")
    g.sites.append({"name": "HOUSE", "player": 1, "footprint": [20, 23, 20, 23], "done": True})   # room for both units
    g.queues[TC] = [{"name": "VILLAGER_MALE", "player": 1, "progress": 0}]
    g.queues[BARRACKS] = [{"name": "MILITIA", "player": 1, "progress": 0}]
    train.tick(g, 5)
    assert g.queues[TC][0]["progress"] == pytest.approx(5 * 1.05 / 25)
    assert g.queues[BARRACKS][0]["progress"] == pytest.approx(5 / train.TRAIN_TIMES["MILITIA"])


def test_the_menu_shows_the_new_time():
    server, g = game("PERSIANS", 3)
    train.open_menu(g, "Steve", (3, 3))
    assert ":Villager:50 food · 20.8 s · queue 0/15" in menus(server)[-1]
    server, g = game("PERSIANS", 3)
    train.open_menu(g, "Steve", (17, 3))
    assert f":Militia:50 food · 20 gold · {train.TRAIN_TIMES['MILITIA']} s · " in menus(server)[-1]
