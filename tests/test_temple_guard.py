"""Temple Guard (#2157): the Muisca barracks trains the temple guard from the Castle Age and researches Elite
Temple Guard in the Imperial Age (AoE2 DE wiki infobox "Temple Guard", revision 1090786). The upgrade turns the live
guards into elite ones, and the barracks then trains the elite one. Only the Muisca have it. Not here: the monastery as a second
building, and the faster attacks in a long fight."""
from test_castle_upgrades import BARRACKS, research, setup
from test_forging import menus

from game import combat, train

CASTLE = ("FEUDAL_AGE", "CASTLE_AGE")
IMPERIAL = CASTLE + ("IMPERIAL_AGE",)
TG, ELITE, UP = "TEMPLE_GUARD", "ELITE_TEMPLE_GUARD", "ELITE_TEMPLE_GUARD_UPGRADE"


def label(name):
    return train.ITEMS[name][2]


def barracks(civ="MUISCA", ages=IMPERIAL):
    server, g = setup(ages=ages)
    g.data["players"] = {"1": {"civ": civ}}
    g.soldiers["tg"] = "TEMPLE_GUARD"
    g.game.entities.setdefault("tg", {"Pos": (0.5, 64.0, 0.5)})          # alive at the census (#3122)
    return server, g


def test_the_menu_has_the_unit_from_the_castle_age_for_the_muisca():
    server, g = barracks(ages=("FEUDAL_AGE",))
    train.open_menu(g, "Steve", BARRACKS)
    assert f":{train.build.LOCKED}:{label(TG)}:" in menus(server)[-1]        # gray: a later age
    server, g = barracks(ages=CASTLE)
    train.open_menu(g, "Steve", BARRACKS)
    menu = menus(server)[-1] + " "
    assert f":{train.ITEMS[TG][1]}:{label(TG)}:" in menu and label(ELITE) not in menu   # the upgrade: the Imperial Age
    for civ in ("BRITONS", "AZTECS"):
        server, g = barracks(civ, CASTLE)
        train.open_menu(g, "Steve", BARRACKS)
        assert label(TG) not in menus(server)[-1], civ
        assert train.queue(g, "Steve", BARRACKS, "TEMPLE_GUARD") is None, civ


def test_the_upgrade_changes_the_live_and_the_new_units():
    server, g = barracks()
    train.open_menu(g, "Steve", BARRACKS)
    assert f":{train.ITEMS[UP][1]}:{label(UP)}:" in menus(server)[-1]
    research(g, BARRACKS, UP)
    assert g.soldiers["tg"] == "ELITE_TEMPLE_GUARD"
    assert combat.stats_command("tg", "ELITE_TEMPLE_GUARD") in server.log
    train.open_menu(g, "Steve", BARRACKS)
    menu = menus(server)[-1] + " "
    assert f":{train.ITEMS[ELITE][1]}:{label(ELITE)}:" in menu
    assert f":{label(TG)}:" not in menu and f":{train.ITEMS[UP][1]}:{label(UP)}:" not in menu
    assert train.queue(g, "Steve", BARRACKS, "ELITE_TEMPLE_GUARD")
    assert train.queue(g, "Steve", BARRACKS, "TEMPLE_GUARD") is None
