"""game/train.py: the archery range researches Cranequins (#2161, AoE2 DE wiki "Cranequins", revision 1081203):
Imperial Age, 300 food, 200 gold, 70 s; the (heavy) mounted crossbowmen get +1 range and +2 attack against infantry.
Only the Britons, Danes, Franks, Saxons, Sicilians and Varangians have it, in place of Parthian Tactics."""
from test_castle_upgrades import RANGE, setup
from test_forging import menus

from game import civs, train

IMPERIAL = ("FEUDAL_AGE", "CASTLE_AGE", "IMPERIAL_AGE")
CIVS = {"BRITONS", "DANES", "FRANKS", "SAXONS", "SICILIANS", "VARANGIANS"}
ITEM = " 29:book:Cranequins:300 food · 200 gold · 70 s · research "


def player(civ="FRANKS", ages=IMPERIAL):
    server, g = setup(ages=ages, techs=())
    g.data.setdefault("players", {}).setdefault("1", {})["civ"] = civ
    g.soldiers["mc"] = "MOUNTED_CROSSBOWMAN"
    g.game.entities.setdefault("mc", {"Pos": (0.5, 64.0, 0.5)})          # alive at the census (#3122)
    return server, g


def test_the_values_are_those_of_the_wiki():
    assert len(train.HELP["CRANEQUINS"]) <= 50                         # the cost and time: ITEM in the menu (#2182)
    assert train.value("age", "CRANEQUINS", 0) == 3


def test_only_six_civilizations_have_it_in_place_of_parthian_tactics():
    names = {r["name"] for r in civs.ROWS}
    assert names - set(civs.MISSING["CRANEQUINS"]) == CIVS
    assert CIVS <= set(civs.MISSING["PARTHIAN_TACTICS"])
    server, g = player()
    train.open_menu(g, "Steve", RANGE)
    assert ITEM in menus(server)[-1] + " "
    server, g = player(ages=("FEUDAL_AGE", "CASTLE_AGE"))
    train.open_menu(g, "Steve", RANGE)
    assert "Cranequins" not in menus(server)[-1]
    server, g = player("MONGOLS")
    train.open_menu(g, "Steve", RANGE)
    assert "Cranequins" not in menus(server)[-1] and train.queue(g, "Steve", RANGE, "CRANEQUINS") is None


def test_the_mounted_crossbowmen_get_range_and_attack_against_infantry():
    server, g = player()
    names = ("MOUNTED_CROSSBOWMAN", "HEAVY_MOUNTED_CROSSBOWMAN", "CAVALRY_ARCHER", "ARCHER")
    old = {n: train.stats(g, n) for n in names}
    rect = train.open_menu(g, "Steve", RANGE)
    assert train.order(g, "Steve", rect, 29) == 1
    train.tick(g, 70)
    assert "CRANEQUINS" in g.techs
    for n in names[:2]:
        o = old[n]
        assert train.stats(g, n) == o._replace(range=o.range + 1, bonus={**o.bonus, "infantry": o.bonus.get("infantry", 0) + 2})
    assert train.stats(g, "MOUNTED_CROSSBOWMAN").range == 5
    for n in names[2:]:
        assert train.stats(g, n) == old[n]
    assert any(c.startswith("aoe stats mc ") for c in server.log), "the live unit"
