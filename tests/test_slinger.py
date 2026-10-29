"""game/train.py: the archery range trains the slinger (#2010, AoE2 DE wiki infobox "Slinger (Age of Empires II)"):
only the civilizations that civs.MISSING does not list for it."""
from test_train_knight import menu, setup

import units
from game import civs, train

RANGE = (11, 3)
UNIT, ITEM, LABEL = train.slots("ARCHERY_RANGE", "SLINGER")
HAVE = sorted({r["name"] for r in civs.ROWS} - set(civs.MISSING["SLINGER"]))   # the civilizations of the data


def player(civ=HAVE[0]):
    server, g = setup("ARCHERY_RANGE")
    g.stock.update(food=10000, wood=10000)
    g.data.setdefault("players", {}).setdefault("1", {})["civ"] = civ
    return server, g


def test_only_the_civilizations_of_the_data_train_it():
    for civ in HAVE:
        server, g = player(civ)
        train.open_menu(g, "Steve", RANGE)
        assert f" {UNIT}:{ITEM}:{LABEL}:" in menu(server), civ
    for civ in sorted(civs.MISSING["SLINGER"])[:2]:
        server, g = player(civ)
        train.open_menu(g, "Steve", RANGE)
        assert f":{LABEL}:" not in menu(server) and train.queue(g, "Steve", RANGE, "SLINGER") is None, civ


def test_a_trained_slinger_has_its_entity_and_cost():
    server, g = player(HAVE[-1])
    assert train.order(g, "Steve", train.open_menu(g, "Steve", RANGE), UNIT) == 1
    price = train.price(g, "SLINGER")
    assert g.stock["food"] == 10000 - price.get("food", 0) and g.stock["wood"] == 10000 - price.get("wood", 0)
    uuid, = train.tick(g, train.TRAIN_TIMES["SLINGER"])
    summon, = [c for c in server.log if c.startswith("summon")]
    assert summon.startswith(f"summon {units.classify('SLINGER')['id']} ")
    assert g.soldiers == {uuid: "SLINGER"}
