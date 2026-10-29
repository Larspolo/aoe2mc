"""game/train.py stats and game/civs.py TWICE: for the Khitans, Forging and Iron Casting give twice the attack (#1561).
The AoE2 wiki, page "Khitans" (MediaWiki API, 2026-10-27): "The effects of Forging and Iron Casting are doubled."."""
import pytest
from test_forging import setup

from game import combat, train


def player(civ, *techs):
    server, g = setup()
    g.data["players"] = {"1": {"civ": civ}}
    g.techs |= {"FEUDAL_AGE", "CASTLE_AGE", *techs}
    return server, g


def more(civ, unit, *techs):
    """The attack that the technologies give to unit of a player of civ; the other values must stay."""
    base, s = train.stats(player(civ)[1], unit), train.stats(player(civ, *techs)[1], unit)
    assert s == base._replace(attack=s.attack), (civ, unit, techs)
    return s.attack - base.attack


@pytest.mark.parametrize("unit", ["MILITIA", "SCOUT_CAVALRY", "HULK"])
def test_each_research_gives_the_khitan_melee_units_and_hulks_twice_the_attack(unit):
    for techs in ((), ("FORGING",), ("FORGING", "IRON_CASTING")):
        assert more("KHITANS", unit, *techs) == 2 * more("BRITONS", unit, *techs), techs
    assert more("BRITONS", unit, "FORGING") > 0


def test_other_technologies_and_units_stay():
    _, base = player("KHITANS")
    _, g = player("KHITANS", "FORGING", "IRON_CASTING", "FLETCHING")
    _, briton = player("BRITONS", "FORGING", "IRON_CASTING", "FLETCHING")
    assert train.stats(g, "ARCHER").attack - train.stats(base, "ARCHER").attack == \
        train.stats(briton, "ARCHER").attack - train.stats(player("BRITONS")[1], "ARCHER").attack > 0   # Fletching once
    for unit in ("VILLAGER_MALE", "MONK"):
        assert train.stats(g, unit) == train.stats(base, unit)


def test_the_live_militia_gets_the_double_attack():
    server, g = player("KHITANS")
    g.soldiers["m"] = "MILITIA"
    train.research(g, {"name": "FORGING", "player": "Steve"})
    s = train.stats(g, "MILITIA")
    assert s.attack == combat.stats("MILITIA").attack + more("KHITANS", "MILITIA", "FORGING")
    assert combat.stats_command("m", "MILITIA", s) in server.log
