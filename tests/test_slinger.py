"""game/train.py: the archery range trains the slinger in the Castle Age (#2010, AoE2 DE wiki infobox "Slinger (Age of
Empires II)" revision 1085955: 50 food, 25 wood, 25 s): only the Incas, Mapuche, Muisca and Tupi. It is a drowned with a
trident, as the skirmisher (units.classify)."""
from test_train_knight import menu, setup

from game import build, civs, train

RANGE = (11, 3)
UNIT = 25                                                              # after the mounted crossbowman (23, 24)


def player(civ="INCAS"):
    server, g = setup("ARCHERY_RANGE")
    g.stock.update(food=10000, wood=10000)
    g.data.setdefault("players", {}).setdefault("1", {})["civ"] = civ
    return server, g


def test_the_values_are_those_of_the_wiki():
    assert build.AGE["SLINGER"] == 2 and len(train.HELP["SLINGER"]) <= 50
    assert train.ITEMS["SLINGER"][0] == UNIT


def test_only_the_incas_mapuche_muisca_and_tupi_train_it():
    for civ in ("INCAS", "MAPUCHE", "MUISCA", "TUPI"):
        server, g = player(civ)
        train.open_menu(g, "Steve", RANGE)
        assert f" {UNIT}:drowned_spawn_egg:Slinger:" in menu(server), civ               # Incas: their food discount
    for civ in ("FRANKS", "AZTECS"):
        server, g = player(civ)
        train.open_menu(g, "Steve", RANGE)
        assert "Slinger" not in menu(server) and train.queue(g, "Steve", RANGE, "SLINGER") is None, civ


def test_a_trained_slinger_is_a_drowned_with_a_trident():
    server, g = player("TUPI")
    train.open_menu(g, "Steve", RANGE)
    assert f" {UNIT}:drowned_spawn_egg:Slinger:50 food · 25 wood · 25 s · queue 0/15" in menu(server)
    assert train.order(g, "Steve", train.open_menu(g, "Steve", RANGE), UNIT) == 1
    assert g.stock["food"] == 10000 - 50 and g.stock["wood"] == 10000 - 25
    uuid, = train.tick(g, 25)
    summon, = [c for c in server.log if c.startswith("summon")]
    assert summon.startswith("summon minecraft:drowned ") and "minecraft:trident" in summon
    assert g.soldiers == {uuid: "SLINGER"}


def test_the_civilizations_of_the_wiki():
    have = set().union(*civs.MISSING.values()) - set(civs.MISSING["SLINGER"])
    assert have == {"INCAS", "MAPUCHE", "MUISCA", "TUPI"}
