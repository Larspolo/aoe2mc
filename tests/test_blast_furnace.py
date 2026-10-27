"""game/train.py: the blacksmith researches Blast Furnace (infantry and cavalry +2 attack, 275 food, 225 gold, 100 s)
in the Imperial Age, after Iron Casting, in the slot of Forging (#1451, AoE2 DE wiki infobox)."""
import pytest
from test_forging import menus, setup

from game import civs, train


def imperial(*techs):
    server, g = setup(food=300)
    g.techs |= {"CASTLE_AGE", "IMPERIAL_AGE", "FORGING", *techs}
    g.stock.update(gold=300)
    return server, g


def test_the_menu_shows_blast_furnace_after_iron_casting_in_the_slot_of_forging():
    slot = train.ITEMS["FORGING"][0]
    assert train.ITEMS["BLAST_FURNACE"][0] == slot and train.AFTER["BLAST_FURNACE"] == "IRON_CASTING"
    server, g = imperial()
    train.open_menu(g, "Steve", (11, 3))
    assert ":book:Blast Furnace:" not in menus(server)[-1] and train.queue(g, "Steve", (11, 3), "BLAST_FURNACE") is None
    server, g = imperial("IRON_CASTING")
    train.open_menu(g, "Steve", (11, 3))
    assert f" {slot}:book:Blast Furnace:275 food · 225 gold · 100 s · research " in menus(server)[-1] + " "
    server, g = imperial("IRON_CASTING")
    g.techs.discard("IMPERIAL_AGE")                                # the Castle Age: not yet
    assert train.queue(g, "Steve", (11, 3), "BLAST_FURNACE") is None


@pytest.mark.parametrize("unit", ["MILITIA", "SCOUT_CAVALRY"])
def test_the_research_gives_2_attack_to_the_live_and_the_new_melee_units(unit):
    server, g = imperial("IRON_CASTING")
    old, others = train.stats(g, unit), {n: train.stats(g, n) for n in ("ARCHER", "VILLAGER_MALE", "MONK")}
    rect = train.open_menu(g, "Steve", (11, 3))
    assert train.order(g, "Steve", rect, train.ITEMS["BLAST_FURNACE"][0]) == 1
    train.tick(g, train.TRAIN_TIMES["BLAST_FURNACE"])
    assert "BLAST_FURNACE" in g.techs and train.stats(g, unit) == old._replace(attack=old.attack + 2)
    assert {n: train.stats(g, n) for n in others} == others        # not the archers, villagers and monks
    assert any(c.startswith("aoe stats ") for c in server.log)     # the live units get the new values


def test_the_civilization_bonuses_of_the_blacksmith_cover_blast_furnace():
    assert "BLAST_FURNACE" in civs.SMITH                           # Bulgarians, Spanish
    assert any("BLAST_FURNACE" in what and change == (0.0,) * 4 for what, _, change in civs.COSTS["MAGYARS"])   # free
