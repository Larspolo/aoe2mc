"""game/train.py: the blacksmith researches the Castle Age armor lines (#1394, AoE2 DE wiki infoboxes): Chain Mail Armor
(infantry, 200 food, 100 gold, 55 s), Chain Barding Armor (cavalry, 250 food, 150 gold, 60 s) and Leather Archer Armor
(archers, 150 food, 150 gold, 55 s), each +1 melee and +1 pierce armor, each after its Feudal Age armor, in its slot."""
import pytest
from test_forging import menus, setup

from game import civs, combat, train

LINES = [("CHAIN_MAIL_ARMOR", "SCALE_MAIL_ARMOR", "Chain Mail Armor", "200 food · 100 gold · 55 s", "MILITIA"),
         ("CHAIN_BARDING_ARMOR", "SCALE_BARDING_ARMOR", "Chain Barding Armor", "250 food · 150 gold · 60 s", "SCOUT_CAVALRY"),
         ("LEATHER_ARCHER_ARMOR", "PADDED_ARCHER_ARMOR", "Leather Archer Armor", "150 food · 150 gold · 55 s", "ARCHER")]


def castle(*techs):
    server, g = setup(food=300)
    g.techs |= {"CASTLE_AGE", *techs}
    g.stock.update(gold=200)
    return server, g


@pytest.mark.parametrize("tech, before, label, cost, unit", LINES)
def test_the_menu_shows_the_castle_armor_after_its_feudal_armor_in_its_slot(tech, before, label, cost, unit):
    slot = train.ITEMS[before][0]
    assert train.ITEMS[tech][0] == slot and train.AFTER[tech] == before
    server, g = castle()
    train.open_menu(g, "Steve", (11, 3))
    assert f":book:{label}:" not in menus(server)[-1] and train.queue(g, "Steve", (11, 3), tech) is None
    server, g = castle(before)
    train.open_menu(g, "Steve", (11, 3))
    assert f" {slot}:book:{label}:{cost} · research " in menus(server)[-1] + " "
    server, g = setup(food=300)                                    # the Feudal Age: not yet
    g.techs.add(before)
    assert train.queue(g, "Steve", (11, 3), tech) is None


@pytest.mark.parametrize("tech, before, label, cost, unit", LINES)
def test_the_research_gives_the_class_one_melee_and_one_pierce_armor(tech, before, label, cost, unit):
    server, g = castle(before)
    old = train.stats(g, unit)
    rect = train.open_menu(g, "Steve", (11, 3))
    assert train.order(g, "Steve", rect, train.ITEMS[tech][0]) == 1
    train.tick(g, train.TRAIN_TIMES[tech])
    assert tech in g.techs
    assert train.stats(g, unit) == old._replace(melee=old.melee + 1, pierce=old.pierce + 1)
    assert train.stats(g, "VILLAGER_MALE") == combat.stats("VILLAGER_MALE")
    assert any(c.startswith("aoe stats ") for c in server.log)     # the live units get the new armor


def test_the_civilization_bonuses_of_the_blacksmith_cover_the_castle_armor():
    assert {"CHAIN_MAIL_ARMOR", "CHAIN_BARDING_ARMOR", "LEATHER_ARCHER_ARMOR"} <= set(civs.SMITH)   # Bulgarians, Spanish
