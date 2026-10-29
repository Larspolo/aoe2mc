"""game/civs.py: Persian town centers and docks train and research faster in each age, by the factors of civs.WORK_RATE
(AoE2 DE wiki, "Persians", #1894); other buildings and civilizations keep the AoE2 times."""
import pytest
from test_castle_upgrades import entry
from test_forging import menus, setup

from game import civs, train

TC, BARRACKS = (2, 5, 2, 5), (16, 19, 2, 5)
AGES = ("FEUDAL_AGE", "CASTLE_AGE", "IMPERIAL_AGE")
RATE = civs.WORK_RATE["PERSIANS"]


def game(civ, age=0):
    server, g = setup(age=0)
    g.data["players"] = {"1": {"civ": civ}}
    g.techs.update(AGES[:age])
    return server, g


@pytest.mark.parametrize("age", range(4))
def test_a_persian_villager_trains_faster_in_each_age(age):
    _, g = game("PERSIANS", age)
    assert train.seconds(g, "VILLAGER_MALE", "TOWN_CENTER") == pytest.approx(
        train.TRAIN_TIMES["VILLAGER_MALE"] / RATE["TOWN_CENTER"][age])
    assert train.seconds(g, "FISHING_SHIP", "DOCK") == pytest.approx(train.TRAIN_TIMES["FISHING_SHIP"] / RATE["DOCK"][age])


def test_the_feudal_age_research_is_faster_and_a_briton_villager_is_not():
    _, g = game("PERSIANS")
    assert train.seconds(g, "FEUDAL_AGE", "TOWN_CENTER") == pytest.approx(train.TRAIN_TIMES["FEUDAL_AGE"] / RATE["TOWN_CENTER"][0])
    _, g = game("BRITONS", 3)
    assert train.seconds(g, "VILLAGER_MALE", "TOWN_CENTER") == train.TRAIN_TIMES["VILLAGER_MALE"]


def test_the_queue_of_the_town_center_ends_sooner_and_the_barracks_not():
    _, g = game("PERSIANS")
    g.sites.append({"name": "HOUSE", "player": 1, "footprint": [20, 23, 20, 23], "done": True})   # room for both units
    g.queues[TC] = [{"name": "VILLAGER_MALE", "player": 1, "progress": 0}]
    g.queues[BARRACKS] = [{"name": "MILITIA", "player": 1, "progress": 0}]
    train.tick(g, 5)
    assert g.queues[TC][0]["progress"] == pytest.approx(5 * RATE["TOWN_CENTER"][0] / train.TRAIN_TIMES["VILLAGER_MALE"])
    assert g.queues[BARRACKS][0]["progress"] == pytest.approx(5 / train.TRAIN_TIMES["MILITIA"])


def test_the_menu_shows_the_new_time():
    server, g = game("PERSIANS", 3)
    train.open_menu(g, "Steve", (3, 3))
    villager = entry(g, (3, 3), "VILLAGER_MALE")
    assert villager + "queue 0/15" in menus(server)[-1]
    assert f" · {train.TRAIN_TIMES['VILLAGER_MALE']} s · " not in villager       # the new time
    server, g = game("PERSIANS", 3)
    train.open_menu(g, "Steve", (17, 3))
    assert entry(g, (17, 3), "MILITIA") in menus(server)[-1]
    assert f" · {train.TRAIN_TIMES['MILITIA']} s · " in entry(g, (17, 3), "MILITIA")
