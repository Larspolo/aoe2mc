"""game/train.py: an own archery range trains the hand cannoneer in the Imperial Age, only after Chemistry, with its
AoE2 DE cost and time (#1506). Values: the AoE2 wiki infobox "Hand_Cannoneer" (MediaWiki API, 2026-10-27: Food 45,
Gold 50, Time 34, TrainReq Chemistry, HP 40, PAttack 17, Range 7, ROF 3.45)."""
import re

from test_gather import FakeServer, grid
from test_loom import menus

from game import combat, gather, train

build = train.build                                                    # the module that train uses
RANGE = (2, 6, 2, 6)                                                   # block footprint (x0, x1, z0, z1)


def setup(ages=3, techs=()):
    objects = [{"kind": "building", "name": "ARCHERY_RANGE", "player": 1, "tile": [4.0, 4.0], "footprint": [2, 2, 6, 6]},
               {"kind": "building", "name": "HOUSE", "player": 1, "tile": [11.0, 11.0], "footprint": [10, 10, 12, 12]}]
    server = FakeServer({})
    g = gather.Gather(server, grid([[64] * 16 for _ in range(16)], objects)).setup()
    g.techs |= set(build.AGE_TECHS[:ages]) | set(techs)
    g.stock.update(food=1000, gold=1000)
    return server, g


def test_the_hand_cannoneer_has_the_aoe2_cost_time_and_age():
    assert (train.COSTS["HAND_CANNONEER"], train.TRAIN_TIMES["HAND_CANNONEER"], build.AGE["HAND_CANNONEER"]) \
        == ({"food": 45, "gold": 50}, 34, 3)
    assert "HAND_CANNONEER" in train.TRAINS["ARCHERY_RANGE"] and train.HELP["HAND_CANNONEER"]
    assert build.NEEDS["HAND_CANNONEER"] == "CHEMISTRY"
    assert combat.stats("HAND_CANNONEER")[:5] == (40, 17, 1, 0, 7)                    # HP, attack, armor, range


def test_the_hand_cannoneer_is_gray_before_the_imperial_age_and_before_chemistry():
    server, g = setup(ages=2, techs=["CHEMISTRY"])
    assert build.locked(g, "HAND_CANNONEER") == "Needs the Imperial Age"
    server, g = setup()
    assert build.locked(g, "HAND_CANNONEER") == "Needs Chemistry"
    train.open_menu(g, "Steve", (3, 3))
    assert " 7:gray_dye:Hand Cannoneer:45 food · 50 gold · 34 s · Needs Chemistry" in menus(server)[-1]
    assert not train.queue(g, "Steve", (3, 3), "HAND_CANNONEER") and g.stock["food"] == 1000
    server, g = setup(techs=["CHEMISTRY"])
    train.open_menu(g, "Steve", (3, 3))
    assert " 7:pillager_spawn_egg:Hand Cannoneer:45 food · 50 gold · 34 s · queue 0/15" in menus(server)[-1]


def test_a_trained_hand_cannoneer_shoots_with_its_values():
    server, g = setup(techs=["CHEMISTRY"])
    assert train.order(g, "Steve", RANGE, 7) == 1 and (g.stock["food"], g.stock["gold"]) == (955, 950)
    assert train.tick(g, 33) == []
    uuid, = train.tick(g, 1)
    summon, = [c for c in server.log if c.startswith("summon")]
    assert re.match(r"summon minecraft:pillager ", summon)
    s = train.stats(g, "HAND_CANNONEER")
    assert s.attack == combat.stats("HAND_CANNONEER").attack                   # Chemistry: no +1 for gunpowder units
    assert combat.stats_command(uuid, "HAND_CANNONEER", s) in server.log
    assert combat.range_command(uuid, "HAND_CANNONEER", g.map.T, s=s) in server.log
    assert g.soldiers[uuid] == "HAND_CANNONEER"
