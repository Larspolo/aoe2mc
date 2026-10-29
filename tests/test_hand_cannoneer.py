"""game/train.py: an own archery range trains the hand cannoneer in the Imperial Age, only after Chemistry, with its
AoE2 DE cost and time (#1506, the AoE2 wiki infobox "Hand_Cannoneer")."""
import re

from menu_line import item
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


def test_the_hand_cannoneer_is_gray_before_its_age_and_before_its_technology():
    age, need = build.AGE["HAND_CANNONEER"], build.NEEDS["HAND_CANNONEER"]
    server, g = setup(ages=age - 1, techs=[need])
    assert build.locked(g, "HAND_CANNONEER").startswith("Needs the ")      # an age
    server, g = setup(ages=age)
    lock = build.locked(g, "HAND_CANNONEER")
    assert lock and not lock.startswith("Needs the ")                      # the technology
    train.open_menu(g, "Steve", (3, 3))
    assert item(menus(server)[-1], "Hand Cannoneer").split(":")[1] == "gray_dye"
    assert item(menus(server)[-1], "Hand Cannoneer").endswith(" · " + lock)
    assert not train.queue(g, "Steve", (3, 3), "HAND_CANNONEER") and g.stock["food"] == 1000
    server, g = setup(ages=age, techs=[need])
    train.open_menu(g, "Steve", (3, 3))
    assert item(menus(server)[-1], "Hand Cannoneer").endswith(" · queue 0/15")


def test_a_trained_hand_cannoneer_shoots_with_its_values():
    server, g = setup(techs=["CHEMISTRY"])
    cost, t = train.price(g, "HAND_CANNONEER"), train.seconds(g, "HAND_CANNONEER", "ARCHERY_RANGE")
    assert train.order(g, "Steve", RANGE, train.SLOTS["HAND_CANNONEER"]) == 1
    assert (g.stock["food"], g.stock["gold"]) == (1000 - cost.get("food", 0), 1000 - cost.get("gold", 0))
    assert train.tick(g, t - 1) == []
    uuid, = train.tick(g, 1)
    summon, = [c for c in server.log if c.startswith("summon")]
    assert re.match(r"summon minecraft:pillager ", summon)
    s = train.stats(g, "HAND_CANNONEER")
    assert s.attack == combat.stats("HAND_CANNONEER").attack                   # Chemistry: no +1 for gunpowder units
    assert combat.stats_command(uuid, "HAND_CANNONEER", s) in server.log
    assert combat.range_command(uuid, "HAND_CANNONEER", g.map.T, s=s) in server.log
    assert g.soldiers[uuid] == "HAND_CANNONEER"
