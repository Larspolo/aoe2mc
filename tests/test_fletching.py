"""game/train.py: the blacksmith menu has "Fletching" next to "Forging" (a book, 100 food and 50 gold, 30 AoE2
seconds). A click queues it once; after the research the live and the new archers have +1 attack and +1 range
(combat.range_command), and militia and scouts do not change (#724)."""
from urllib.parse import unquote

from test_gather import FakeServer, grid

from game import combat, gather, train


def setup(food=100, gold=50, age=1):
    """A flat 24 × 24 map (tile size 1): a town center of player 1 at blocks x 2-4, z 2-4 (population room), an
    archery range at x 16-18, z 2-4, a built blacksmith at x 10-12, z 2-4, a militia, a scout and an archer."""
    objects = [{"kind": "building", "name": "TOWN_CENTER", "player": 1, "tile": [3.5, 3.5], "footprint": [2, 2, 5, 5]},
               {"kind": "building", "name": "ARCHERY_RANGE", "player": 1, "tile": [17.5, 3.5], "footprint": [16, 2, 19, 5]},
               {"kind": "unit", "name": "MILITIA", "player": 1, "uuid": "m", "tile": [9.5, 9.5]},
               {"kind": "unit", "name": "SCOUT_CAVALRY", "player": 1, "uuid": "s", "tile": [11.5, 11.5]},
               {"kind": "unit", "name": "ARCHER", "player": 1, "uuid": "a", "tile": [13.5, 13.5]}]
    server = FakeServer({u: {"Pos": (p, 64.0, p)} for u, p in (("m", 9.5), ("s", 11.5), ("a", 13.5))})
    g = gather.Gather(server, grid([[64] * 24 for _ in range(24)], objects)).setup()
    g.sites.append({"name": "BLACKSMITH", "player": 1, "footprint": [10, 13, 2, 5], "done": True})
    g.stock.update(food=food, gold=gold)
    g.techs.update({"FEUDAL_AGE"} if age else ())                   # a Feudal Age technology (the key "age", #1046)
    return server, g


def menus(server):
    return [unquote(c) for c in server.log if c.startswith("aoe menu ")]


def test_the_blacksmith_menu_has_fletching_next_to_forging():
    server, g = setup()
    train.open_menu(g, "Steve", (11, 3))
    assert menus(server)[0].startswith("aoe menu Steve Blacksmith 0:book:Forging:150 food · 50 s · research ")
    assert " 2:book:Fletching:100 food · 50 gold · 30 s · research " in menus(server)[0] + " "


def test_a_click_queues_fletching_once_and_takes_its_cost():
    server, g = setup(food=1000, gold=1000)
    rect = train.open_menu(g, "Steve", (11, 3))
    assert train.order(g, "Steve", rect, 2, shift=True) == 1 and (g.stock["food"], g.stock["gold"]) == (900, 950)
    assert train.order(g, "Steve", rect, 2) == 0 and (g.stock["food"], g.stock["gold"]) == (900, 950)
    assert " 2:book:Fletching:100 food · 50 gold · 30 s · researching " in menus(server)[-1] + " "


def test_fletching_gives_archers_one_attack_and_one_range():
    server, g = setup()
    rect = train.open_menu(g, "Steve", (11, 3))
    train.order(g, "Steve", rect, 2)
    train.tick(g, 29)
    assert g.techs == {"FEUDAL_AGE"} and not [c for c in server.log if c.startswith(("aoe stats", "aoe range"))]
    train.tick(g, 1)
    assert g.techs == {"FEUDAL_AGE", "FLETCHING"} and not any(g.queues.values())
    for name in ("ARCHER", "CROSSBOWMAN", "SKIRMISHER", "CAVALRY_ARCHER", "LONGBOWMAN"):
        s = combat.stats(name)
        assert train.stats(g, name) == s._replace(attack=s.attack + 1, range=s.range + 1), name
    for name in ("MILITIA", "SCOUT_CAVALRY", "VILLAGER_MALE", "MANGONEL"):
        assert train.stats(g, name) == combat.stats(name), name
    assert sorted(c for c in server.log if c.startswith(("aoe stats", "aoe range"))) == \
        ["aoe range a 5 24", combat.stats_command("a", "ARCHER", train.stats(g, "ARCHER"))]   # range 4 + 1 tiles, T 1
    assert any("Fletching is researched." in c for c in server.log if c.startswith("tellraw"))
    train.open_menu(g, "Steve", (11, 3))
    assert "Fletching" not in menus(server)[-1] and "Forging" in menus(server)[-1]


def test_a_new_archer_has_the_fletching_range():
    server, g = setup(food=0, gold=45)
    g.stock.update(wood=25)
    g.techs.update({"FEUDAL_AGE", "FLETCHING"})                        # archers are a Feudal Age unit (#674)
    assert train.queue(g, "Steve", (17, 3), "ARCHER")
    uuid, = train.tick(g, 35)
    assert combat.stats_command(uuid, "ARCHER", train.stats(g, "ARCHER")) in server.log
    assert f"aoe range {uuid} 5 24" in server.log
