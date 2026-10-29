"""Arbalester and Heavy Cavalry Archer (#1500): the archery range researches both upgrades in the Imperial Age, the
arbalester in the slot of Crossbowman after it (the UpCost and UpTime of the AoE2 DE wiki infoboxes "Crossbowman" and
"Cavalry Archer"). Then the live units of the line are the new units, and the archery range trains them."""
from menu_line import item
from test_castle_upgrades import RANGE, research
from test_forging import menus
from test_gather import FakeServer, grid

from game import combat, gather, train

IMPERIAL = ("FEUDAL_AGE", "CASTLE_AGE", "IMPERIAL_AGE")
LIVE = (("c", "CROSSBOWMAN"), ("h", "CAVALRY_ARCHER"))


def setup(ages=IMPERIAL, techs=("CROSSBOWMAN_UPGRADE",)):
    """A flat 24 × 24 map (tile size 1): a built archery range of player 1, a crossbowman and a cavalry archer."""
    objects = [{"kind": "unit", "name": n, "player": 1, "uuid": u, "tile": [3.5 + 3 * i, 12.5]}
               for i, (u, n) in enumerate(LIVE)]
    server = FakeServer({u: {"Pos": (3.5 + 3 * i, 64.0, 12.5)} for i, (u, _) in enumerate(LIVE)})
    g = gather.Gather(server, grid([[64] * 24 for _ in range(24)], objects)).setup()
    g.sites.append({"name": "ARCHERY_RANGE", "player": 1, "footprint": [8, 11, 2, 5], "done": True})
    g.stock.update(food=10000, wood=10000, gold=10000)
    g.techs.update(ages + techs)
    return server, g


def test_the_upgrades_are_in_the_menu_in_the_imperial_age():
    server, g = setup(ages=IMPERIAL[:2])
    train.open_menu(g, "Steve", RANGE)
    assert ":Arbalester:" not in menus(server)[-1] and ":Heavy Cavalry Archer:" not in menus(server)[-1]
    g.techs.add("IMPERIAL_AGE")
    train.open_menu(g, "Steve", RANGE)
    menu = menus(server)[-1]
    assert item(menu, "Arbalester").endswith(" · research") and item(menu, "Heavy Cavalry Archer").endswith(" · research")
    server, g = setup(techs=())
    train.open_menu(g, "Steve", RANGE)
    assert ":book:Arbalester:" not in menus(server)[-1]                # not before Crossbowman


def test_the_live_units_and_the_archery_range_get_the_new_units():
    server, g = setup()
    for tech, (u, unit) in (("ARBALESTER_UPGRADE", ("c", "ARBALESTER")),
                            ("HEAVY_CAVALRY_ARCHER_UPGRADE", ("h", "HEAVY_CAVALRY_ARCHER"))):
        research(g, RANGE, tech)
        assert g.soldiers[u] == unit
        assert combat.stats_command(u, unit, train.stats(g, unit)) in server.log
        assert combat.label_command(u, unit) in server.log
    train.open_menu(g, "Steve", RANGE)
    menu = menus(server)[-1]
    assert item(menu, "Arbalester").endswith(" · queue 0/15") and item(menu, "Heavy Cavalry Archer").endswith(" · queue 0/15")
    assert ":Crossbowman:" not in menu and ":Cavalry Archer:" not in menu
    assert train.queue(g, "Steve", RANGE, "ARBALESTER") and train.queue(g, "Steve", RANGE, "HEAVY_CAVALRY_ARCHER")
    assert train.queue(g, "Steve", RANGE, "CROSSBOWMAN") is None
