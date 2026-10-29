"""game/train.py: the blacksmith researches Iron Casting (infantry and cavalry attack) and Bodkin Arrow (archers attack)
in the Castle Age, each after its Feudal Age technology (#1395)."""
import pytest
from test_castle_upgrades import entry
from test_forging import menus, setup

from game import combat, train

LINES = [("IRON_CASTING", "MILITIA"), ("IRON_CASTING", "SCOUT_CAVALRY"), ("BODKIN_ARROW", "ARCHER")]


def castle(*techs):
    server, g = setup(food=300)
    g.techs |= {"CASTLE_AGE", *techs}
    g.stock.update(gold=200)
    return server, g


@pytest.mark.parametrize("tech, unit", LINES)
def test_the_menu_shows_the_castle_technology_after_its_feudal_technology(tech, unit):
    before, label = train.BY_KEY["after"][tech], train.ITEMS[tech][2]
    server, g = castle()
    train.open_menu(g, "Steve", (11, 3))
    assert f":book:{label}:" not in menus(server)[-1] and train.queue(g, "Steve", (11, 3), tech) is None
    server, g = castle(before)
    train.open_menu(g, "Steve", (11, 3))
    assert " " + entry(g, (11, 3), tech) + "research " in menus(server)[-1] + " "
    server, g = setup(food=300)                                    # the Feudal Age: not yet
    g.techs.add(before)
    assert train.queue(g, "Steve", (11, 3), tech) is None


@pytest.mark.parametrize("tech, unit", LINES)
def test_the_research_gives_the_new_attack_to_the_live_and_the_new_units(tech, unit):
    server, g = castle(train.BY_KEY["after"][tech])
    old = train.stats(g, unit)
    rect = train.open_menu(g, "Steve", (11, 3))
    assert train.order(g, "Steve", rect, train.ITEMS[tech][0]) == 1
    train.tick(g, train.TRAIN_TIMES[tech])
    assert tech in g.techs
    assert train.stats(g, unit).attack > old.attack
    assert train.stats(g, "VILLAGER_MALE") == combat.stats("VILLAGER_MALE")
    assert train.stats(g, "MONK") == combat.stats("MONK")
    assert any(c.startswith("aoe stats ") for c in server.log)     # the live units get the new values
