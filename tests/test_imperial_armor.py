"""game/train.py: the blacksmith researches the Imperial Age armor (#1452, AoE2 DE wiki infobox): Plate Mail Armor
(infantry), Ring Archer Armor (archers) and Plate Barding Armor (cavalry) give +1 melee and +2 pierce armor, each
after its Castle Age armor and in its slot."""
import pytest
from test_forging import menus, setup

from game import civs, train

TECHS = {"PLATE_MAIL_ARMOR": ("CHAIN_MAIL_ARMOR", "Plate Mail Armor", "300 food · 150 gold · 70 s", "MILITIA"),
         "RING_ARCHER_ARMOR": ("LEATHER_ARCHER_ARMOR", "Ring Archer Armor", "250 food · 250 gold · 70 s", "ARCHER"),
         "PLATE_BARDING_ARMOR": ("CHAIN_BARDING_ARMOR", "Plate Barding Armor", "350 food · 200 gold · 75 s",
                                 "SCOUT_CAVALRY")}


def imperial(*techs):
    """The Imperial Age, with the technologies and the Feudal Age armor before each one."""
    techs += tuple(train.AFTER[t] for t in techs if t in train.AFTER)
    server, g = setup(food=400)
    g.techs |= {"CASTLE_AGE", "IMPERIAL_AGE", *techs}
    g.stock.update(gold=300)
    return server, g


@pytest.mark.parametrize("tech", TECHS)
def test_the_menu_shows_the_imperial_armor_after_its_castle_age_armor(tech):
    before, label, cost, _ = TECHS[tech]
    slot = train.ITEMS[before][0]
    assert train.ITEMS[tech][0] == slot and train.AFTER[tech] == before
    assert len(train.HELP[tech]) <= 50
    server, g = imperial()
    train.open_menu(g, "Steve", (11, 3))
    assert f":book:{label}:" not in menus(server)[-1] and train.queue(g, "Steve", (11, 3), tech) is None
    server, g = imperial(before)
    train.open_menu(g, "Steve", (11, 3))
    assert f" {slot}:book:{label}:{cost} · research " in menus(server)[-1] + " "
    assert menus(server)[-1].count(f" {slot}:book:") == 1                 # only the Imperial armor in its slot
    server, g = imperial(before)
    g.techs.discard("IMPERIAL_AGE")                                # the Castle Age: not yet
    assert train.queue(g, "Steve", (11, 3), tech) is None


@pytest.mark.parametrize("tech", TECHS)
def test_the_research_gives_1_melee_and_2_pierce_armor_to_its_class(tech):
    before, _, _, unit = TECHS[tech]
    server, g = imperial(before)
    names = ("MILITIA", "ARCHER", "SCOUT_CAVALRY", "CAVALRY_ARCHER", "VILLAGER_MALE", "MONK")
    old = {n: train.stats(g, n) for n in names}
    rect = train.open_menu(g, "Steve", (11, 3))
    assert train.order(g, "Steve", rect, train.ITEMS[tech][0]) == 1
    train.tick(g, train.TRAIN_TIMES[tech])
    assert tech in g.techs
    new = {n: train.stats(g, n) for n in names}
    hit = {unit, "CAVALRY_ARCHER"} if tech == "RING_ARCHER_ARMOR" else {unit}   # a cavalry archer is an archer
    for n in names:
        assert new[n] == (old[n]._replace(melee=old[n].melee + 1, pierce=old[n].pierce + 2) if n in hit else old[n]), n
    assert any(c.startswith("aoe stats ") for c in server.log)     # the live units get the new values


def test_the_civilization_bonuses_of_the_blacksmith_cover_the_imperial_armor():
    assert set(TECHS) <= set(civs.SMITH)                           # Bulgarians, Spanish
    free = {c: set().union(*(w for w, _, ch in civs.COSTS[c] if isinstance(w, tuple) and ch == (0.0,) * 4))
            for c in ("KOREANS", "MALAY")}
    assert "RING_ARCHER_ARMOR" in free["KOREANS"] and "PLATE_MAIL_ARMOR" in free["MALAY"]   # AoE2 wiki bonuses
