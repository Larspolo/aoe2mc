"""game/train.py: an own siege workshop trains the bombard cannon in the Imperial Age, only after Chemistry, with its
AoE2 DE cost and time (#1380)."""
import re

from menu_line import item
from test_gather import FakeServer, grid
from test_loom import menus

import units
from game import combat, gather, train

build = train.build                                                    # the module that train uses
SHOP = (2, 6, 2, 6)                                                    # block footprint (x0, x1, z0, z1)


def setup(ages=3, techs=()):
    objects = [{"kind": "building", "name": "SIEGE_WORKSHOP", "player": 1, "tile": [4.0, 4.0], "footprint": [2, 2, 6, 6]},
               {"kind": "building", "name": "HOUSE", "player": 1, "tile": [11.0, 11.0], "footprint": [10, 10, 12, 12]}]
    server = FakeServer({})
    g = gather.Gather(server, grid([[64] * 16 for _ in range(16)], objects)).setup()
    g.techs |= set(build.AGE_TECHS[:ages]) | set(techs)
    g.stock.update(wood=1000, gold=1000)
    return server, g


def text(g, name, building=None):
    """The cost and time text of the menu item of name, from the data (as train.show writes it)."""
    return (" · ".join(f"{v} {r}" for r, v in train.price(g, name, building).items()) or "free") + \
        f" · {round(train.seconds(g, name, building), 1):g} s · "


def test_the_bombard_cannon_is_gray_before_the_imperial_age_and_before_chemistry():
    server, g = setup(ages=2, techs=["CHEMISTRY"])
    assert build.locked(g, "BOMBARD_CANNON") == "Needs the Imperial Age"
    server, g = setup()
    assert build.locked(g, "BOMBARD_CANNON") == "Needs Chemistry"
    train.open_menu(g, "Steve", (3, 3))
    line = item(menus(server)[-1], "Bombard Cannon")
    assert ":gray_dye:Bombard Cannon:" in line and line.endswith(text(g, "BOMBARD_CANNON", "SIEGE_WORKSHOP") + "Needs Chemistry")
    assert not train.queue(g, "Steve", (3, 3), "BOMBARD_CANNON") and g.stock["wood"] == 1000
    server, g = setup(techs=["CHEMISTRY"])
    train.open_menu(g, "Steve", (3, 3))
    assert item(menus(server)[-1], "Bombard Cannon").endswith(":Bombard Cannon:" + text(g, "BOMBARD_CANNON", "SIEGE_WORKSHOP") +
                                                               "queue 0/15")


def test_a_trained_bombard_cannon_shoots_with_its_values_and_minimum_range():
    server, g = setup(techs=["CHEMISTRY"])
    cost, t = train.price(g, "BOMBARD_CANNON", "SIEGE_WORKSHOP"), train.seconds(g, "BOMBARD_CANNON", "SIEGE_WORKSHOP")
    assert train.order(g, "Steve", SHOP, train.ITEMS["BOMBARD_CANNON"][0]) == 1
    assert (g.stock["wood"], g.stock["gold"]) == (1000 - cost.get("wood", 0), 1000 - cost.get("gold", 0))
    assert train.tick(g, t - 1) == []
    uuid, = train.tick(g, 1)
    summon, = [c for c in server.log if c.startswith("summon")]
    assert units.siege("BOMBARD_CANNON") and re.match(r"summon minecraft:minecart ", summon)
    s = train.stats(g, "BOMBARD_CANNON")
    assert s.attack == combat.stats("BOMBARD_CANNON").attack                   # Chemistry: no +1 for gunpowder (#1506)
    assert combat.stats_command(uuid, "BOMBARD_CANNON", s) in server.log
    shot = combat.range_command(uuid, "BOMBARD_CANNON", g.map.T, s=s)
    assert shot in server.log and shot.split()[-1] == f"{combat.MIN_RANGE['BOMBARD_CANNON'] * g.map.T}"   # minimum range
    assert g.soldiers[uuid] == "BOMBARD_CANNON"
