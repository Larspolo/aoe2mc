"""Camel Scout (#2130): the stable of the Gurjaras trains the camel scout from the Feudal Age. The Castle Age upgrades
the live camel scouts to camel riders, and the stable then trains camel riders only (wiki: "automatically upgraded to Camel Riders
upon reaching the Castle Age")."""
from test_castle_upgrades import STABLE, entry, setup
from test_forging import menus

from game import combat, train

FEUDAL = ("FEUDAL_AGE",)


def stable(civ="GURJARAS", ages=FEUDAL):
    server, g = setup(ages=ages, techs=())
    g.data["players"] = {"1": {"civ": civ}}
    g.soldiers["cs"] = "CAMEL_SCOUT"
    return server, g


def test_the_help_text_is_short():
    assert len(train.HELP["CAMEL_SCOUT"]) <= 50


def test_the_stable_of_the_gurjaras_has_it_from_the_feudal_age():
    server, g = stable()
    train.open_menu(g, "Steve", STABLE)
    assert " " + entry(g, STABLE, "CAMEL_SCOUT") + "queue 0/15 " in menus(server)[-1] + " "
    assert train.queue(g, "Steve", STABLE, "CAMEL_SCOUT")
    server, g = stable("BRITONS")
    train.open_menu(g, "Steve", STABLE)
    assert "Camel Scout" not in menus(server)[-1]
    assert train.queue(g, "Steve", STABLE, "CAMEL_SCOUT") is None


def test_the_castle_age_makes_the_live_and_the_new_units_camel_riders():
    server, g = stable()
    train.research(g, {"name": "CASTLE_AGE"})
    assert g.soldiers["cs"] == "CAMEL_RIDER"
    assert combat.stats_command("cs", "CAMEL_RIDER", train.stats(g, "CAMEL_RIDER")) in server.log
    assert train.trains(g, "STABLE").count("CAMEL_RIDER") == 1 and "CAMEL_SCOUT" not in train.trains(g, "STABLE")
    assert train.queue(g, "Steve", STABLE, "CAMEL_SCOUT") is None
    assert train.queue(g, "Steve", STABLE, "CAMEL_RIDER")


def test_the_castle_age_stays_for_civilizations_without_camels():
    for civ in ("BRITONS", "GURJARAS"):
        server, g = stable(civ)
        assert train.unlocked(g, "CASTLE_AGE")
