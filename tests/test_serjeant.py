"""Serjeant (#1748): the castle of the Sicilians researches Elite Serjeant in the Imperial Age. The upgrade changes the
live and the new units."""
from test_train_castle import setup

from game import train

CASTLE = (12, 4)


def test_the_upgrade_changes_the_live_and_the_new_units():
    server, g = setup("SICILIANS", food=2000, wood=0, gold=2000, ages=3)
    g.soldiers["se"] = "SERJEANT"
    g.game.entities.setdefault("se", {"Pos": (0.5, 64.0, 0.5)})          # alive at the census (#3122)
    train.open_menu(g, "Steve", CASTLE)
    assert train.queue(g, "Steve", CASTLE, "ELITE_SERJEANT_UPGRADE")
    train.tick(g, train.TRAIN_TIMES["ELITE_SERJEANT_UPGRADE"])
    assert "ELITE_SERJEANT_UPGRADE" in g.techs and g.soldiers["se"] == "ELITE_SERJEANT"
    assert train.queue(g, "Steve", CASTLE, "ELITE_SERJEANT")
    assert train.queue(g, "Steve", CASTLE, "SERJEANT") is None
