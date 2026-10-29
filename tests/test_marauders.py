"""Unique technology of the Huns (#2687): the castle of the Huns researches Marauders in the Castle Age (AoE2 DE wiki
"Marauders"). After it the stable trains the Tarkan, and the Elite Tarkan after the upgrade at the castle (civs.TRAINS,
the key "after")."""
from menu_line import item
from test_forging import menus
from test_train_knight import setup

from game import train

STABLE = (11, 3)


def player(civ="HUNS", ages=2):
    server, g = setup("STABLE", ages=("FEUDAL_AGE", "CASTLE_AGE")[:ages])
    g.stock.update(food=10000, gold=10000, wood=10000)
    g.data.setdefault("players", {}).setdefault("1", {})["civ"] = civ
    return server, g


def test_the_castle_of_the_huns_researches_marauders_in_the_castle_age():
    server, g = player()
    assert "MARAUDERS" in train.trains(g, "CASTLE")
    assert train.unlocked(g, "MARAUDERS") and not train.unlocked(player(ages=1)[1], "MARAUDERS")


def test_the_stable_trains_the_tarkan_only_after_marauders():
    server, g = player()
    assert "TARKAN" not in train.trains(g, "STABLE")
    train.open_menu(g, "Steve", STABLE)
    assert "Tarkan" not in menus(server)[-1]
    g.techs.add("MARAUDERS")
    assert "TARKAN" in train.trains(g, "STABLE")
    assert "ELITE_TARKAN_UPGRADE" not in train.trains(g, "STABLE")       # the upgrade stays at the castle
    slot = train.slots("STABLE", "TARKAN")[0]
    train.open_menu(g, "Steve", STABLE)
    tarkan = item(menus(server)[-1], "Tarkan")
    assert tarkan.startswith(f"{slot}:") and tarkan.endswith(" · queue 0/15")
    assert "Elite Tarkan" not in menus(server)[-1]


def test_the_stable_trains_the_elite_tarkan_after_the_upgrade():
    server, g = player(ages=3)
    g.techs.update({"MARAUDERS", "ELITE_TARKAN_UPGRADE"})
    out = train.trains(g, "STABLE")
    assert "ELITE_TARKAN" in out and "TARKAN" not in out


def test_a_frank_has_no_marauders_and_no_tarkan_at_the_stable():
    server, g = player(civ="FRANKS")
    assert "MARAUDERS" not in train.trains(g, "CASTLE")
    g.techs.add("MARAUDERS")
    assert "TARKAN" not in train.trains(g, "STABLE")
