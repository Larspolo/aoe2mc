"""Shotel Warrior (#1725): the castle of the Ethiopians researches Elite Shotel Warrior in the Imperial Age. The
upgrade changes the live and the new units."""
from test_train_castle import setup

from game import combat, train

CASTLE = (12, 4)


def test_the_upgrade_changes_the_live_and_the_new_units():
    server, g = setup("ETHIOPIANS", food=2000, wood=0, gold=2000, ages=3)
    g.soldiers["sw"] = "SHOTEL_WARRIOR"
    g.game.entities.setdefault("sw", {"Pos": (0.5, 64.0, 0.5)})          # alive at the census (#3122)
    train.open_menu(g, "Steve", CASTLE)
    assert train.queue(g, "Steve", CASTLE, "ELITE_SHOTEL_WARRIOR_UPGRADE")
    train.tick(g, train.TRAIN_TIMES["ELITE_SHOTEL_WARRIOR_UPGRADE"])
    assert "ELITE_SHOTEL_WARRIOR_UPGRADE" in g.techs and g.soldiers["sw"] == "ELITE_SHOTEL_WARRIOR"
    assert combat.stats_command("sw", "ELITE_SHOTEL_WARRIOR") in server.log
    assert train.queue(g, "Steve", CASTLE, "ELITE_SHOTEL_WARRIOR")
    assert train.queue(g, "Steve", CASTLE, "SHOTEL_WARRIOR") is None
