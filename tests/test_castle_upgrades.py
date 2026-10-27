"""game/train.py: the Castle Age unit upgrades of AoE2 DE (#1396). The barracks researches Long Swordsman (after
Man-at-Arms) and Pikeman, the archery range Crossbowman and Elite Skirmisher, the stable Light Cavalry. Each one turns
the live units of its line into the next unit, and the building trains the new unit."""
import pytest
from test_forging import menus
from test_gather import FakeServer, grid

from game import combat, gather, train

BARRACKS, RANGE, STABLE = (3, 3), (9, 3), (15, 3)                 # a block cell in each building
UPGRADES = {"LONG_SWORDSMAN_UPGRADE": ({"food": 150, "gold": 65}, 40),   # AoE2 DE wiki: UpCost, UpTime of the unit
            "PIKEMAN_UPGRADE": ({"food": 160, "gold": 90}, 35),          # before
            "CROSSBOWMAN_UPGRADE": ({"food": 175, "gold": 100}, 35),
            "ELITE_SKIRMISHER_UPGRADE": ({"wood": 230, "gold": 130}, 50),
            "LIGHT_CAVALRY_UPGRADE": ({"food": 150, "gold": 50}, 45)}
UNITS = {"LONG_SWORDSMAN": ({"food": 50, "gold": 20}, 21), "PIKEMAN": ({"food": 35, "wood": 25}, 22),   # wiki infobox
         "CROSSBOWMAN": ({"wood": 25, "gold": 45}, 27), "ELITE_SKIRMISHER": ({"food": 25, "wood": 35}, 22),
         "LIGHT_CAVALRY": ({"food": 80}, 30)}
LIVE = (("a", "MAN_AT_ARMS"), ("p", "SPEARMAN"), ("c", "ARCHER"), ("k", "SKIRMISHER"), ("l", "SCOUT_CAVALRY"))


def setup(ages=("FEUDAL_AGE", "CASTLE_AGE"), techs=("MAN_AT_ARMS_UPGRADE",)):
    """A flat 24 × 24 map (tile size 1): a built barracks, archery range and stable of player 1, one unit of each line."""
    objects = [{"kind": "unit", "name": n, "player": 1, "uuid": u, "tile": [3.5 + 3 * i, 12.5]}
               for i, (u, n) in enumerate(LIVE)]
    server = FakeServer({u: {"Pos": (3.5 + 3 * i, 64.0, 12.5)} for i, (u, _) in enumerate(LIVE)})
    g = gather.Gather(server, grid([[64] * 24 for _ in range(24)], objects)).setup()
    g.sites += [{"name": n, "player": 1, "footprint": [x, x + 3, 2, 5], "done": True}
                for n, x in (("BARRACKS", 2), ("ARCHERY_RANGE", 8), ("STABLE", 14))]
    g.stock.update(food=10000, wood=10000, gold=10000)
    g.techs.update(ages + techs)
    return server, g


def research(g, cell, name):
    assert train.queue(g, "Steve", cell, name), name
    train.tick(g, train.TRAIN_TIMES[name])
    assert name in g.techs


@pytest.mark.parametrize("name", sorted(UPGRADES))
def test_each_upgrade_has_the_wiki_cost_time_and_the_castle_age(name):
    cost, time = UPGRADES[name]
    assert train.COSTS[name] == cost and train.TRAIN_TIMES[name] == time and train.TECH_AGE[name] == 2


@pytest.mark.parametrize("name", sorted(UNITS))
def test_each_new_unit_has_the_wiki_cost_time_and_combat_values(name):
    cost, time = UNITS[name]
    assert train.COSTS[name] == cost and train.TRAIN_TIMES[name] == time
    assert name in combat.STATS and name in train.ITEMS and name in train.HELP


def test_no_upgrade_in_the_feudal_age():
    server, g = setup(ages=("FEUDAL_AGE",))
    for cell in (RANGE, STABLE):
        train.open_menu(g, "Steve", cell)
        assert not {"Crossbowman", "Elite Skirmisher", "Light Cavalry"} & set(menus(server)[-1].split(":"))
    assert train.queue(g, "Steve", BARRACKS, "PIKEMAN_UPGRADE") is None


def test_long_swordsman_only_after_man_at_arms_in_its_slot():
    server, g = setup(techs=())
    train.open_menu(g, "Steve", BARRACKS)
    menu = menus(server)[-1] + " "
    assert " 2:book:Man-at-Arms:" in menu and "Long Swordsman" not in menu
    assert " 3:book:Pikeman:160 food · 90 gold · 35 s · research " in menu
    research(g, BARRACKS, "MAN_AT_ARMS_UPGRADE")
    train.open_menu(g, "Steve", BARRACKS)
    assert " 2:book:Long Swordsman:150 food · 65 gold · 40 s · research " in menus(server)[-1] + " "


def test_the_live_units_and_the_buildings_get_the_new_units():
    server, g = setup()
    for cell, name in ((BARRACKS, "LONG_SWORDSMAN_UPGRADE"), (BARRACKS, "PIKEMAN_UPGRADE"), (RANGE, "CROSSBOWMAN_UPGRADE"),
                       (RANGE, "ELITE_SKIRMISHER_UPGRADE"), (STABLE, "LIGHT_CAVALRY_UPGRADE")):
        research(g, cell, name)
    assert [g.soldiers[u] for u, _ in LIVE] == ["LONG_SWORDSMAN", "PIKEMAN", "CROSSBOWMAN", "ELITE_SKIRMISHER",
                                               "LIGHT_CAVALRY"]
    for u, n in (("a", "LONG_SWORDSMAN"), ("l", "LIGHT_CAVALRY")):
        assert combat.stats_command(u, n, train.stats(g, n)) in server.log
    assert train.trains(g, "BARRACKS")[:2] == ("LONG_SWORDSMAN", "PIKEMAN")
    assert train.trains(g, "ARCHERY_RANGE")[:2] == ("CROSSBOWMAN", "ELITE_SKIRMISHER")
    assert train.trains(g, "STABLE")[0] == "LIGHT_CAVALRY"
    train.open_menu(g, "Steve", BARRACKS)
    menu = menus(server)[-1] + " "
    assert " 0:zombie_spawn_egg:Long Swordsman:50 food · 20 gold · 21 s" in menu and ":book:Pikeman:" not in menu
