"""game/train.py: the blacksmith researches Blast Furnace (infantry and cavalry more attack) in the Imperial Age,
after Iron Casting, in the slot of Forging (#1451)."""
import pytest
from menu_line import item
from test_forging import menus, setup

from game import train


def text(g, name, building=None):
    """The cost and time text of the menu item of name, from the data (as train.show writes it)."""
    return (" · ".join(f"{v} {r}" for r, v in train.price(g, name, building).items()) or "free") + \
        f" · {round(train.seconds(g, name, building), 1):g} s · "


def imperial(*techs):
    server, g = setup(food=300)
    g.techs |= {"CASTLE_AGE", "IMPERIAL_AGE", "FORGING", *techs}
    g.stock.update(gold=300)
    return server, g


def test_the_menu_shows_blast_furnace_after_iron_casting_in_the_slot_of_forging():
    slot = train.ITEMS["FORGING"][0]
    server, g = imperial()
    train.open_menu(g, "Steve", (11, 3))
    assert ":book:Blast Furnace:" not in menus(server)[-1] and train.queue(g, "Steve", (11, 3), "BLAST_FURNACE") is None
    server, g = imperial("IRON_CASTING")
    train.open_menu(g, "Steve", (11, 3))
    assert item(menus(server)[-1], "Blast Furnace") == f"{slot}:book:Blast Furnace:" + text(g, "BLAST_FURNACE") + "research"
    server, g = imperial("IRON_CASTING")
    g.techs.discard("IMPERIAL_AGE")                                # the Castle Age: not yet
    assert train.queue(g, "Steve", (11, 3), "BLAST_FURNACE") is None


@pytest.mark.parametrize("unit", ["MILITIA", "SCOUT_CAVALRY"])
def test_the_research_gives_attack_to_the_live_and_the_new_melee_units(unit):
    server, g = imperial("IRON_CASTING")
    old, others = train.stats(g, unit), {n: train.stats(g, n) for n in ("ARCHER", "VILLAGER_MALE", "MONK")}
    rect = train.open_menu(g, "Steve", (11, 3))
    assert train.order(g, "Steve", rect, train.ITEMS["BLAST_FURNACE"][0]) == 1
    train.tick(g, train.TRAIN_TIMES["BLAST_FURNACE"])
    new = train.stats(g, unit)
    assert "BLAST_FURNACE" in g.techs and new.attack > old.attack and new == old._replace(attack=new.attack)
    assert {n: train.stats(g, n) for n in others} == others        # not the archers, villagers and monks
    assert any(c.startswith("aoe stats ") for c in server.log)     # the live units get the new values
