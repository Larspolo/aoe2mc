"""game/train.py: the blacksmith menu has "Padded Archer Armor" in the Feudal Age (a book, the cost and time of the
data). After the research the archers of the player (also cavalry archers and skirmishers) have more melee and pierce
armor, as in AoE2 (#937)."""
from menu_line import item
from test_forging import menus, setup

from game import combat, train


def feudal(food=100):
    server, g = setup(food=food)
    g.techs.add("FEUDAL_AGE")
    return server, g


def test_no_padded_archer_armor_in_the_dark_age():
    server, g = setup(food=100, age=0)
    train.open_menu(g, "Steve", (11, 3))
    assert "Padded Archer Armor" not in menus(server)[-1]                # a technology shows from its age (unlocked)
    assert train.queue(g, "Steve", (11, 3), "PADDED_ARCHER_ARMOR") is None and g.stock["food"] == 100


def test_the_blacksmith_menu_has_padded_archer_armor_in_the_feudal_age():
    server, g = feudal()
    train.open_menu(g, "Steve", (11, 3))
    assert item(menus(server)[-1], "Padded Archer Armor").endswith(" · research")


def test_padded_archer_armor_gives_archers_melee_and_pierce_armor():
    server, g = feudal(food=1000)
    rect = train.open_menu(g, "Steve", (11, 3))
    slot, left = train.SLOTS["PADDED_ARCHER_ARMOR"], 1000 - train.price(g, "PADDED_ARCHER_ARMOR")["food"]
    assert train.order(g, "Steve", rect, slot, shift=True) == 1 and g.stock["food"] == left
    assert train.order(g, "Steve", rect, slot) == 0 and g.stock["food"] == left      # only once
    train.tick(g, train.seconds(g, "PADDED_ARCHER_ARMOR", "BLACKSMITH") - 1)
    assert g.techs == {"FEUDAL_AGE"}
    train.tick(g, 1)
    assert "PADDED_ARCHER_ARMOR" in g.techs
    for name in ("ARCHER", "SKIRMISHER", "CAVALRY_ARCHER", "LONGBOWMAN"):
        s, t = combat.stats(name), train.stats(g, name)
        assert t.melee > s.melee and t.pierce > s.pierce and t._replace(melee=s.melee, pierce=s.pierce) == s, name
    for name in ("MILITIA", "VILLAGER_MALE", "SCOUT_CAVALRY", "SPEARMAN"):
        assert train.stats(g, name) == combat.stats(name), name
    stats = [c for c in server.log if c.startswith("aoe stats")]
    assert stats == [combat.stats_command("a", "ARCHER", train.stats(g, "ARCHER"))]     # the live archer
    assert any("Padded Archer Armor is researched." in c for c in server.log if c.startswith("tellraw"))
