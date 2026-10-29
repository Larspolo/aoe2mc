"""Shrivamsha Rider (#1612): the stable of the Gurjaras researches Elite Shrivamsha Rider in the Imperial Age. The
upgrade changes the live and the new units."""
from test_castle_upgrades import STABLE, research, setup

from game import combat, train

IMPERIAL = ("FEUDAL_AGE", "CASTLE_AGE", "IMPERIAL_AGE")


def stable(civ="GURJARAS", ages=IMPERIAL):
    server, g = setup(ages=ages)
    g.data["players"] = {"1": {"civ": civ}}
    g.soldiers["sr"] = "SHRIVAMSHA_RIDER"
    g.game.entities.setdefault("sr", {"Pos": (0.5, 64.0, 0.5)})          # alive at the census (#3122)
    return server, g


def test_the_upgrade_changes_the_live_and_the_new_units():
    server, g = stable()
    train.open_menu(g, "Steve", STABLE)
    research(g, STABLE, "ELITE_SHRIVAMSHA_RIDER_UPGRADE")
    assert g.soldiers["sr"] == "ELITE_SHRIVAMSHA_RIDER"
    assert combat.stats_command("sr", "ELITE_SHRIVAMSHA_RIDER") in server.log
    assert train.queue(g, "Steve", STABLE, "ELITE_SHRIVAMSHA_RIDER")
    assert train.queue(g, "Steve", STABLE, "SHRIVAMSHA_RIDER") is None
