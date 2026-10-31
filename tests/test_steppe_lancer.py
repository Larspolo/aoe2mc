"""Steppe Lancer (#1557): the stable of the Cumans, Jurchens, Khitans, Mongols and Tatars researches Elite Steppe Lancer
in the Imperial Age. The upgrade turns the live steppe lancers into elite ones, and the stable then trains the elite
steppe lancer."""
from test_castle_upgrades import STABLE, research, setup

from game import combat, train

IMPERIAL = ("FEUDAL_AGE", "CASTLE_AGE", "IMPERIAL_AGE")


def stable(civ="CUMANS", ages=IMPERIAL):   # no bonus to the hit points (the Mongols: +30 %)
    server, g = setup(ages=ages)
    g.data["players"] = {"1": {"civ": civ}}
    g.soldiers["sl"] = "STEPPE_LANCER"
    g.game.entities.setdefault("sl", {"Pos": (0.5, 64.0, 0.5)})          # alive at the census (#3122)
    return server, g


def test_the_upgrade_changes_the_live_and_the_new_units():
    server, g = stable()
    train.open_menu(g, "Steve", STABLE)
    research(g, STABLE, "ELITE_STEPPE_LANCER_UPGRADE")
    assert g.soldiers["sl"] == "ELITE_STEPPE_LANCER"
    assert combat.stats_command("sl", "ELITE_STEPPE_LANCER", T=g.map.T) in server.log
    assert train.queue(g, "Steve", STABLE, "ELITE_STEPPE_LANCER") and train.queue(g, "Steve", STABLE, "STEPPE_LANCER") is None
