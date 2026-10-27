"""game/train.py: the blacksmith researches Iron Casting (infantry and cavalry +1 attack, 220 food, 120 gold, 75 s) and
Bodkin Arrow (archers +1 attack and +1 range, 200 food, 100 gold, 35 s) in the Castle Age, each after its Feudal Age
technology, in its slot (#1395, AoE2 DE wiki infoboxes)."""
import pytest
from test_forging import menus, setup

from game import civs, combat, train

LINES = [("IRON_CASTING", "FORGING", "Iron Casting", "220 food · 120 gold · 75 s", "MILITIA", dict(attack=1)),
         ("IRON_CASTING", "FORGING", "Iron Casting", "220 food · 120 gold · 75 s", "SCOUT_CAVALRY", dict(attack=1)),
         ("BODKIN_ARROW", "FLETCHING", "Bodkin Arrow", "200 food · 100 gold · 35 s", "ARCHER", dict(attack=1, range=1))]


def castle(*techs):
    server, g = setup(food=300)
    g.techs |= {"CASTLE_AGE", *techs}
    g.stock.update(gold=200)
    return server, g


@pytest.mark.parametrize("tech, before, label, cost, unit, more", LINES)
def test_the_menu_shows_the_castle_technology_after_its_feudal_technology_in_its_slot(tech, before, label, cost, unit, more):
    slot = train.ITEMS[before][0]
    assert train.ITEMS[tech][0] == slot and train.AFTER[tech] == before and train.TECH_AGE[tech] == 2
    server, g = castle()
    train.open_menu(g, "Steve", (11, 3))
    assert f":book:{label}:" not in menus(server)[-1] and train.queue(g, "Steve", (11, 3), tech) is None
    server, g = castle(before)
    train.open_menu(g, "Steve", (11, 3))
    assert f" {slot}:book:{label}:{cost} · research " in menus(server)[-1] + " "
    server, g = setup(food=300)                                    # the Feudal Age: not yet
    g.techs.add(before)
    assert train.queue(g, "Steve", (11, 3), tech) is None


@pytest.mark.parametrize("tech, before, label, cost, unit, more", LINES)
def test_the_research_gives_the_new_attack_to_the_live_and_the_new_units(tech, before, label, cost, unit, more):
    server, g = castle(before)
    old = train.stats(g, unit)
    rect = train.open_menu(g, "Steve", (11, 3))
    assert train.order(g, "Steve", rect, train.ITEMS[tech][0]) == 1
    train.tick(g, train.TRAIN_TIMES[tech])
    assert tech in g.techs
    assert train.stats(g, unit) == old._replace(**{k: getattr(old, k) + v for k, v in more.items()})
    assert train.stats(g, "VILLAGER_MALE") == combat.stats("VILLAGER_MALE")
    assert train.stats(g, "MONK") == combat.stats("MONK")
    assert any(c.startswith("aoe stats ") for c in server.log)     # the live units get the new values


def test_the_civilization_bonuses_of_the_blacksmith_cover_the_castle_attack():
    assert {"IRON_CASTING", "BODKIN_ARROW"} <= set(civs.SMITH)    # Bulgarians, Spanish
    assert any("IRON_CASTING" in what and change == (0.0,) * 4 for what, _, change in civs.COSTS["MAGYARS"])   # free
