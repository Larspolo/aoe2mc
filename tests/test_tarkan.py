"""Tarkan (#1726): the castle of the Huns researches Elite Tarkan in the Imperial Age. The upgrade changes the live and
the new units."""
from test_train_castle import setup

from game import train

CASTLE = (12, 4)


def test_the_upgrade_changes_the_live_and_the_new_units():
    server, g = setup("HUNS", food=2000, wood=0, gold=2000, ages=3)
    g.soldiers["ta"] = "TARKAN"
    g.game.entities.setdefault("ta", {"Pos": (0.5, 64.0, 0.5)})          # alive at the census (#3122)
    train.open_menu(g, "Steve", CASTLE)
    assert train.queue(g, "Steve", CASTLE, "ELITE_TARKAN_UPGRADE")
    train.tick(g, train.TRAIN_TIMES["ELITE_TARKAN_UPGRADE"])
    assert "ELITE_TARKAN_UPGRADE" in g.techs and g.soldiers["ta"] == "ELITE_TARKAN"
    assert train.queue(g, "Steve", CASTLE, "ELITE_TARKAN")
    assert train.queue(g, "Steve", CASTLE, "TARKAN") is None
