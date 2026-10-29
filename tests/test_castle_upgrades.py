"""game/train.py: the Castle Age unit upgrades of AoE2 DE (#1396). The barracks researches Long Swordsman (after
Man-at-Arms) and Pikeman, the archery range Crossbowman and Elite Skirmisher, the stable Light Cavalry. Each one turns
the live units of its line into the next unit, and the building trains the new unit."""
import pytest
from test_forging import menus
from test_gather import FakeServer, grid

from game import combat, gather, train

BARRACKS, RANGE, STABLE = (3, 3), (9, 3), (15, 3)                 # a block cell in each building
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


def entry(g, cell, name):
    """The menu text of name in the building at cell up to its state, from the data: slot, item, label, cost and time."""
    rect = train.home(g, cell)
    slot, item, label = train.layout(g, rect)[name]
    cost = " · ".join(f"{v} {r}" for r, v in train.price(g, name, train.homes(g)[rect]).items()) or "free"
    item = train.build.LOCKED if train.build.locked(g, name) else item
    return f"{slot}:{item}:{label}:{cost} · {round(train.seconds(g, name, train.homes(g)[rect]), 1):g} s · "


def research(g, cell, name):
    assert train.queue(g, "Steve", cell, name), name
    train.tick(g, train.TRAIN_TIMES[name])
    assert name in g.techs


@pytest.mark.parametrize("name", ["CROSSBOWMAN", "ELITE_SKIRMISHER", "LIGHT_CAVALRY", "LONG_SWORDSMAN", "PIKEMAN"])
def test_each_new_unit_has_combat_values_a_menu_item_and_a_help_text(name):
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
    slot = entry(g, BARRACKS, "MAN_AT_ARMS_UPGRADE").split(":")[0]
    assert " " + entry(g, BARRACKS, "MAN_AT_ARMS_UPGRADE") in menu and "Long Swordsman" not in menu
    assert " " + entry(g, BARRACKS, "PIKEMAN_UPGRADE") + "research " in menu
    research(g, BARRACKS, "MAN_AT_ARMS_UPGRADE")
    train.open_menu(g, "Steve", BARRACKS)
    assert " " + entry(g, BARRACKS, "LONG_SWORDSMAN_UPGRADE") + "research " in menus(server)[-1] + " "
    assert entry(g, BARRACKS, "LONG_SWORDSMAN_UPGRADE").split(":")[0] == slot      # the slot of Man-at-Arms


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
    assert " " + entry(g, BARRACKS, "LONG_SWORDSMAN") in menu and ":book:Pikeman:" not in menu
