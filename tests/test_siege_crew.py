"""The mob in the minecart of each siege unit (#1664, owner decision on #1525): the converter, the trained units and
the size of the trebuchet crew when it packs and unpacks."""
import numpy as np
import pytest
from test_train_castle import setup

import mcvalid
import units
from game import trebuchet

SIEGE = ("BATTERING_RAM", "BOMBARD_CANNON", "CAPPED_RAM", "HEAVY_SCORPION", "HOUFNICE", "MANGONEL", "ONAGER", "SCORPION",
         "SIEGE_ONAGER", "SIEGE_RAM", "SIEGE_TOWER", "TREBUCHET", "TREBUCHET_PACKED")


def crew(name):
    nbt = units.make_entity({"name": name, "player": 1, "x": 0, "y": 0}, {}, (0.5, 64, 0.5), np.random.default_rng(0))
    assert nbt["id"] == "minecraft:minecart" and len(nbt["Passengers"]) == 1
    return nbt["Passengers"][0]


@pytest.mark.parametrize("name", SIEGE)
def test_each_siege_unit_has_a_valid_crew_mob_with_its_scale(name):
    c = crew(name)
    kind = str(c["id"]).removeprefix("minecraft:")
    assert mcvalid.entity_error(str(c["id"])) is None
    assert [(str(a["id"]), float(a["base"])) for a in c["attributes"]] == [("minecraft:scale", pytest.approx(units.siege_scale(name)))]
    assert (c["NoAI"], c["Silent"]) == (1, 1)                         # no walk, jump, shot, attack or sound by itself
    assert str(c["CustomName"]["text"]) == units.pretty(name)          # the crew has the name line, as before
    assert (c.get("IsImmuneToZombification") == 1) == (kind == "piglin")
    assert (str(c["equipment"]["mainhand"]["id"]) == "minecraft:crossbow") if kind == "piglin" else "equipment" not in c


@pytest.mark.parametrize("name", ["ORGAN_GUN", "ROCKET_CART", "COBRA_CAR", "HUSSITE_WAGON"])
def test_the_carts_keep_their_crew(name):
    c = crew(name)
    assert mcvalid.entity_error(str(c["id"])) is None and "attributes" not in c


def test_the_heroes_of_the_trebuchet_get_the_crew_of_the_trebuchet():
    assert units.classify("WARWOLF", True)["Passengers"][0]["id"] == crew("TREBUCHET")["id"]
    assert units.siege_scale("BAD_NEIGHBOR_PACKED") == pytest.approx(units.siege_scale("TREBUCHET_PACKED"))


def test_the_trebuchet_crew_changes_its_size_when_it_packs_and_unpacks():
    server, g = setup()
    g.soldiers["t"] = "TREBUCHET"
    trebuchet.tick(g, 0.0)                                             # a trebuchet of the map: the packed size
    small, big = (f"execute as t on passengers run attribute @s minecraft:scale base set {units.siege_scale(n)}"
                  for n in ("TREBUCHET_PACKED", "TREBUCHET"))
    assert small in server.log
    trebuchet.unpack(g, "t", "fort")
    trebuchet.tick(g, trebuchet.PACK)
    assert server.log.count(big) == 1 and trebuchet.state(g, "t") == "unpacked"
    trebuchet.move(g, "t", [])
    trebuchet.tick(g, trebuchet.PACK)
    assert server.log.count(small) == 2 and server.log.index(big) < len(server.log) - 1 - server.log[::-1].index(small)
