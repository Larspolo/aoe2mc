"""game/train.py: an own siege workshop trains the bombard cannon in the Imperial Age, only after Chemistry, with its
AoE2 DE cost and time (#1380). Values: the AoE2 wiki infobox "Bombard_Cannon" (MediaWiki API, 2026-10-27: Time 56,
Wood 225, Gold 225, TrainReq Chemistry)."""
import re

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


def test_the_bombard_cannon_has_the_aoe2_cost_time_and_age():
    assert (train.COSTS["BOMBARD_CANNON"], train.TRAIN_TIMES["BOMBARD_CANNON"], build.AGE["BOMBARD_CANNON"]) \
        == ({"wood": 225, "gold": 225}, 56, 3)
    assert "BOMBARD_CANNON" in train.TRAINS["SIEGE_WORKSHOP"] and train.HELP["BOMBARD_CANNON"]
    assert build.NEEDS["BOMBARD_CANNON"] == "CHEMISTRY"


def test_the_bombard_cannon_is_gray_before_the_imperial_age_and_before_chemistry():
    server, g = setup(ages=2, techs=["CHEMISTRY"])
    assert build.locked(g, "BOMBARD_CANNON") == "Needs the Imperial Age"
    server, g = setup()
    assert build.locked(g, "BOMBARD_CANNON") == "Needs Chemistry"
    train.open_menu(g, "Steve", (3, 3))
    assert "7:gray_dye:Bombard Cannon:225 wood · 225 gold · 56 s · Needs Chemistry" in menus(server)[-1]
    assert not train.queue(g, "Steve", (3, 3), "BOMBARD_CANNON") and g.stock["wood"] == 1000
    server, g = setup(techs=["CHEMISTRY"])
    train.open_menu(g, "Steve", (3, 3))
    assert "7:tnt_minecart:Bombard Cannon:225 wood · 225 gold · 56 s · queue 0/15" in menus(server)[-1]


def test_a_trained_bombard_cannon_shoots_with_its_values_and_minimum_range():
    server, g = setup(techs=["CHEMISTRY"])
    assert train.order(g, "Steve", SHOP, 7) == 1 and (g.stock["wood"], g.stock["gold"]) == (775, 775)
    assert train.tick(g, 55) == []
    uuid, = train.tick(g, 1)
    summon, = [c for c in server.log if c.startswith("summon")]
    assert units.siege("BOMBARD_CANNON") and re.match(r"summon minecraft:minecart ", summon)
    s = train.stats(g, "BOMBARD_CANNON")
    assert s.attack == combat.stats("BOMBARD_CANNON").attack + 1               # Chemistry: +1 for ranged siege
    assert combat.stats_command(uuid, "BOMBARD_CANNON", s) in server.log
    shot = combat.range_command(uuid, "BOMBARD_CANNON", g.map.T, s=s)
    assert shot in server.log and shot.split()[-2:] == [f"{0.5 * g.map.T}", f"{5 * g.map.T}"]   # blast, minimum range
    assert g.soldiers[uuid] == "BOMBARD_CANNON"
