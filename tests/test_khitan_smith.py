"""game/train.py stats and game/civs.py TWICE: for the Khitans, Forging and Iron Casting give +2 attack each, not +1
(#1561). Values: the AoE2 wiki, page "Khitans" (MediaWiki API, 2026-10-27): "The effects of Forging and Iron Casting
are doubled."; the "Hulk" infobox: Forging +1 (+2 for Khitans), Iron Casting +1 (+2 for Khitans)."""
import pytest
from test_forging import setup

from game import combat, train


def player(civ, *techs):
    server, g = setup()
    g.data["players"] = {"1": {"civ": civ}}
    g.techs |= {"FEUDAL_AGE", "CASTLE_AGE", *techs}
    return server, g


@pytest.mark.parametrize("unit", ["MILITIA", "SCOUT_CAVALRY", "HULK"])
@pytest.mark.parametrize("civ, per", [("KHITANS", 2), ("BRITONS", 1)])
def test_each_research_gives_the_melee_units_and_the_hulks_their_attack(unit, civ, per):
    base = player(civ)[1]
    for techs, n in (((), 0), (("FORGING",), 1), (("FORGING", "IRON_CASTING"), 2)):
        g = player(civ, *techs)[1]
        assert train.stats(g, unit) == train.stats(base, unit)._replace(attack=train.stats(base, unit).attack + n * per)


def test_other_technologies_and_units_stay():
    _, base = player("KHITANS")
    _, g = player("KHITANS", "FORGING", "IRON_CASTING", "FLETCHING")
    assert train.stats(g, "ARCHER").attack == train.stats(base, "ARCHER").attack + 1          # Fletching once
    for unit in ("VILLAGER_MALE", "MONK"):
        assert train.stats(g, unit) == train.stats(base, unit)


def test_the_live_militia_gets_plus_2():
    server, g = player("KHITANS")
    g.soldiers["m"] = "MILITIA"
    train.research(g, {"name": "FORGING", "player": "Steve"})
    s = train.stats(g, "MILITIA")
    assert s.attack == combat.stats("MILITIA").attack + 2
    assert combat.stats_command("m", "MILITIA", s) in server.log
