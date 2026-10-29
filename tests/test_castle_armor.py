"""game/train.py: the blacksmith researches the Castle Age armor lines (#1394): Chain Mail Armor (infantry), Chain
Barding Armor (cavalry) and Leather Archer Armor (archers), each more melee and pierce armor, each after its Feudal Age
armor."""
import pytest
from test_castle_upgrades import entry
from test_forging import menus, setup

from game import combat, train

LINES = [("CHAIN_MAIL_ARMOR", "MILITIA"), ("CHAIN_BARDING_ARMOR", "SCOUT_CAVALRY"), ("LEATHER_ARCHER_ARMOR", "ARCHER")]


def castle(*techs):
    server, g = setup(food=300)
    g.techs |= {"CASTLE_AGE", *techs}
    g.stock.update(gold=200)
    return server, g


@pytest.mark.parametrize("tech, unit", LINES)
def test_the_menu_shows_the_castle_armor_after_its_feudal_armor(tech, unit):
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
def test_the_research_gives_the_class_more_melee_and_pierce_armor(tech, unit):
    server, g = castle(train.BY_KEY["after"][tech])
    old = train.stats(g, unit)
    rect = train.open_menu(g, "Steve", (11, 3))
    assert train.order(g, "Steve", rect, train.ITEMS[tech][0]) == 1
    train.tick(g, train.TRAIN_TIMES[tech])
    assert tech in g.techs
    new = train.stats(g, unit)
    assert new.melee > old.melee and new.pierce > old.pierce and new._replace(melee=old.melee, pierce=old.pierce) == old
    assert train.stats(g, "VILLAGER_MALE") == combat.stats("VILLAGER_MALE")
    assert any(c.startswith("aoe stats ") for c in server.log)     # the live units get the new armor
