"""The mob in the minecart of each siege unit (#1664, owner decision on #1525): the converter, the trained units and
the size of the trebuchet crew when it packs and unpacks."""
import numpy as np
import pytest
from test_train_castle import setup

import mcvalid
import units
from game import trebuchet

TABLE = {"BATTERING_RAM": ("iron_golem", 0.5), "CAPPED_RAM": ("iron_golem", 0.55), "SIEGE_RAM": ("iron_golem", 0.6),
         "MANGONEL": ("breeze", 0.8), "ONAGER": ("breeze", 0.8), "SIEGE_ONAGER": ("breeze", 0.8),
         "SCORPION": ("piglin", 1.0), "HEAVY_SCORPION": ("piglin", 1.0),
         "TREBUCHET": ("warden", 0.6), "TREBUCHET_PACKED": ("warden", 0.36),
         "BOMBARD_CANNON": ("ghast", 0.3), "HOUFNICE": ("ghast", 0.3), "SIEGE_TOWER": ("sniffer", 0.5)}


def crew(name):
    nbt = units.make_entity({"name": name, "player": 1, "x": 0, "y": 0}, {}, (0.5, 64, 0.5), np.random.default_rng(0))
    assert nbt["id"] == "minecraft:minecart" and len(nbt["Passengers"]) == 1
    return nbt["Passengers"][0]


@pytest.mark.parametrize("name", sorted(TABLE))
def test_each_siege_unit_has_the_mob_of_the_decision(name):
    kind, scale = TABLE[name]
    c = crew(name)
    assert c["id"] == f"minecraft:{kind}" and mcvalid.entity_error(str(c["id"])) is None
    assert [(str(a["id"]), float(a["base"])) for a in c["attributes"]] == [("minecraft:scale", pytest.approx(scale))]
    assert (c["NoAI"], c["Silent"]) == (1, 1)                         # no walk, jump, shot, attack or sound by itself
    assert str(c["CustomName"]["text"]) == units.pretty(name)          # the crew has the name line, as before
    assert (c.get("IsImmuneToZombification") == 1) == (kind == "piglin")
    assert (str(c["equipment"]["mainhand"]["id"]) == "minecraft:crossbow") if kind == "piglin" else "equipment" not in c


@pytest.mark.parametrize("name", ["ORGAN_GUN", "ROCKET_CART", "COBRA_CAR", "HUSSITE_WAGON"])
def test_the_carts_keep_their_crew(name):
    c = crew(name)
    assert str(c["id"]) in ("minecraft:pillager", "minecraft:skeleton") and "attributes" not in c


def test_the_heroes_of_the_trebuchet_get_the_warden():
    assert units.classify("WARWOLF", True)["Passengers"][0]["id"] == "minecraft:warden"
    assert units.siege_scale("BAD_NEIGHBOR_PACKED") == pytest.approx(0.36)


def test_the_trebuchet_crew_changes_its_size_when_it_packs_and_unpacks():
    server, g = setup()
    g.soldiers["t"] = "TREBUCHET"
    trebuchet.tick(g, 0.0)                                             # a trebuchet of the map: the packed size
    small, big = (f"execute as t on passengers run attribute @s minecraft:scale base set {s}" for s in ("0.36", "0.6"))
    assert small in server.log
    trebuchet.unpack(g, "t", "fort")
    trebuchet.tick(g, trebuchet.PACK)
    assert server.log.count(big) == 1 and trebuchet.state(g, "t") == "unpacked"
    trebuchet.move(g, "t", [])
    trebuchet.tick(g, trebuchet.PACK)
    assert server.log.count(small) == 2 and server.log.index(big) < len(server.log) - 1 - server.log[::-1].index(small)
