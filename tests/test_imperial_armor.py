"""game/train.py: the blacksmith researches the Imperial Age armor (#1452, AoE2 DE wiki infobox): Plate Mail Armor
(infantry), Ring Archer Armor (archers) and Plate Barding Armor (cavalry) give more melee and pierce armor, each after
its Castle Age armor and in its slot."""
import pytest
from menu_line import item
from test_forging import menus, setup

from game import train

TECHS = {"PLATE_MAIL_ARMOR": "MILITIA", "RING_ARCHER_ARMOR": "ARCHER", "PLATE_BARDING_ARMOR": "SCOUT_CAVALRY"}   # a unit of its class


def imperial(*techs):
    """The Imperial Age, with the technologies and the Feudal Age armor before each one."""
    techs += tuple(train.BY_KEY["after"][t] for t in techs if t in train.BY_KEY["after"])
    server, g = setup(food=5000)
    g.techs |= {"CASTLE_AGE", "IMPERIAL_AGE", *techs}
    g.stock.update(gold=5000)
    return server, g


@pytest.mark.parametrize("tech", TECHS)
def test_the_menu_shows_the_imperial_armor_after_its_castle_age_armor(tech):
    before, (slot, _, label) = train.BY_KEY["after"][tech], train.ITEMS[tech]
    server, g = imperial()
    train.open_menu(g, "Steve", (11, 3))
    assert f":book:{label}:" not in menus(server)[-1] and train.queue(g, "Steve", (11, 3), tech) is None
    server, g = imperial(before)
    train.open_menu(g, "Steve", (11, 3))
    assert item(menus(server)[-1], label).startswith(f"{slot}:book:") and item(menus(server)[-1], label).endswith(" · research")
    assert menus(server)[-1].count(f" {slot}:book:") == 1                 # only the Imperial armor in its slot
    server, g = imperial(before)
    g.techs.discard("IMPERIAL_AGE")                                # the Castle Age: not yet
    assert train.queue(g, "Steve", (11, 3), tech) is None


@pytest.mark.parametrize("tech", TECHS)
def test_the_research_gives_more_melee_and_pierce_armor_to_its_class(tech):
    unit = TECHS[tech]
    server, g = imperial(train.BY_KEY["after"][tech])
    names = ("MILITIA", "ARCHER", "SCOUT_CAVALRY", "CAVALRY_ARCHER", "VILLAGER_MALE", "MONK")
    old = {n: train.stats(g, n) for n in names}
    rect = train.open_menu(g, "Steve", (11, 3))
    assert train.order(g, "Steve", rect, train.ITEMS[tech][0]) == 1
    train.tick(g, train.TRAIN_TIMES[tech])
    assert tech in g.techs
    new = {n: train.stats(g, n) for n in names}
    hit = {unit, "CAVALRY_ARCHER"} if tech == "RING_ARCHER_ARMOR" else {unit}   # a cavalry archer is an archer
    for n in names:
        if n in hit:
            assert new[n].melee > old[n].melee and new[n].pierce > old[n].pierce, n
            assert new[n]._replace(melee=old[n].melee, pierce=old[n].pierce) == old[n], n
        else:
            assert new[n] == old[n], n
    assert any(c.startswith("aoe stats ") for c in server.log)     # the live units get the new values
