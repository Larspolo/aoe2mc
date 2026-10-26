"""game/train.py: the blacksmith menu has "Scale Mail Armor" (a book, 100 food, 40 AoE2 seconds). A click queues it
once; after the research the infantry of the player has +1 melee and +1 pierce armor, also the new units (#725)."""
from test_forging import menus, setup

from game import combat, train


def test_the_blacksmith_menu_has_scale_mail_armor():
    server, g = setup()
    train.open_menu(g, "Steve", (11, 3))
    assert menus(server)[-1].endswith(" 1:book:Scale Mail Armor:100 food · 40 s · research")


def test_a_click_queues_scale_mail_armor_once_and_takes_its_cost():
    server, g = setup(food=1000)
    rect = train.open_menu(g, "Steve", (11, 3))
    assert train.order(g, "Steve", rect, 1, shift=True) == 1 and g.stock["food"] == 900
    assert train.order(g, "Steve", rect, 1) == 0 and g.stock["food"] == 900
    assert menus(server)[-1].endswith("1:book:Scale Mail Armor:100 food · 40 s · researching")


def test_scale_mail_armor_gives_infantry_one_melee_and_pierce_armor():
    server, g = setup()
    rect = train.open_menu(g, "Steve", (11, 3))
    train.order(g, "Steve", rect, 1)
    train.tick(g, 39)
    assert not g.techs
    train.tick(g, 1)
    assert g.techs == {"SCALE_MAIL_ARMOR"}
    for name in ("MILITIA", "SPEARMAN"):
        s = combat.stats(name)
        assert train.stats(g, name) == s._replace(melee=s.melee + 1, pierce=s.pierce + 1), name
    for name in ("VILLAGER_MALE", "ARCHER", "SCOUT_CAVALRY", "KNIGHT", "CAVALRY_ARCHER"):
        assert train.stats(g, name) == combat.stats(name), name
    stats = [c for c in server.log if c.startswith("aoe stats")]
    assert stats == [combat.stats_command("m", "MILITIA", train.stats(g, "MILITIA"))]
    assert "aoe stats m 40 4 1 2 0 infantry -" in stats                # militia: 0/1 armor + 1/1
    assert any("Scale Mail Armor is researched." in c for c in server.log if c.startswith("tellraw"))
    train.open_menu(g, "Steve", (11, 3))
    assert "Scale Mail" not in menus(server)[-1]


def test_a_new_militia_has_the_scale_mail_armor():
    server, g = setup(food=60)
    g.stock.update(gold=20)
    g.techs.add("SCALE_MAIL_ARMOR")
    assert train.queue(g, "Steve", (17, 3), "MILITIA")
    uuid, = train.tick(g, 21)
    assert combat.stats_command(uuid, "MILITIA", train.stats(g, "MILITIA")) in server.log
