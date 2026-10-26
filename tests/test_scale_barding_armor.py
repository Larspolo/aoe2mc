"""game/train.py: the blacksmith menu has "Scale Barding Armor" in the Feudal Age (a book, 150 food, 45 AoE2 seconds).
After the research the cavalry of the player has +1 melee and +1 pierce armor, also the new units (#938)."""
from test_forging import menus, setup

from game import combat, train


def feudal(**stock):
    server, g = setup(**stock)
    g.techs.add("FEUDAL_AGE")
    return server, g


def test_no_scale_barding_armor_in_the_dark_age():
    server, g = setup()
    train.open_menu(g, "Steve", (11, 3))
    assert "Scale Barding" not in menus(server)[-1] and train.queue(g, "Steve", (11, 3), "SCALE_BARDING_ARMOR") is None
    assert g.stock["food"] == 150


def test_the_blacksmith_menu_has_scale_barding_armor_in_the_feudal_age():
    server, g = feudal()
    train.open_menu(g, "Steve", (11, 3))
    assert " 4:book:Scale Barding Armor:150 food · 45 s · research " in menus(server)[-1] + " "


def test_scale_barding_armor_gives_cavalry_one_melee_and_pierce_armor():
    server, g = feudal()
    rect = train.open_menu(g, "Steve", (11, 3))
    assert train.order(g, "Steve", rect, 4) == 1 and g.stock["food"] == 0
    train.tick(g, 44)
    assert g.techs == {"FEUDAL_AGE"}
    train.tick(g, 1)
    assert g.techs == {"FEUDAL_AGE", "SCALE_BARDING_ARMOR"}
    for name in ("SCOUT_CAVALRY", "KNIGHT", "CAMEL_RIDER", "CATAPHRACT"):
        s = combat.stats(name)
        assert train.stats(g, name) == s._replace(melee=s.melee + 1, pierce=s.pierce + 1), name
    for name in ("VILLAGER_MALE", "MILITIA", "ARCHER", "CAVALRY_ARCHER"):
        assert train.stats(g, name) == combat.stats(name), name
    stats = [c for c in server.log if c.startswith("aoe stats")]
    # the scout (a horse with a rider: the horse has the unit UUID and the values, #850): 0/2 armor + 1/1
    assert stats == [combat.stats_command("s", "SCOUT_CAVALRY", train.stats(g, "SCOUT_CAVALRY"))]
    assert stats[0].startswith("aoe stats s 45 3 1 3 0 cavalry ")
    train.open_menu(g, "Steve", (11, 3))
    assert "Scale Barding" not in menus(server)[-1]


def test_a_new_scout_has_the_scale_barding_armor():
    server, g = feudal(food=80)
    g.sites.append({"name": "STABLE", "player": 1, "footprint": [16, 19, 8, 11], "done": True})
    g.techs.add("SCALE_BARDING_ARMOR")
    assert train.queue(g, "Steve", (17, 9), "SCOUT_CAVALRY")
    uuid, = train.tick(g, 30)
    assert combat.stats_command(uuid, "SCOUT_CAVALRY", train.stats(g, "SCOUT_CAVALRY")) in server.log
