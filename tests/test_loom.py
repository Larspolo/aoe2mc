"""game/train.py: the town center menu has "Loom" (a book, 50 gold, 25 AoE2 seconds). A click queues it once; after
the research the villagers have 15 more hit points and 1/2 more armor, and the item leaves the menu (#655)."""
from urllib.parse import unquote

from test_gather import FakeServer, grid
from test_train_menu import FEUDAL

from game import combat, gather, train


def setup(food=0, gold=50):
    """A flat 16 × 16 map (tile size 1): a town center of player 1 at blocks x 2-4, z 2-4, a villager and a militia."""
    objects = [{"kind": "building", "name": "TOWN_CENTER", "player": 1, "tile": [3.5, 3.5], "footprint": [2, 2, 5, 5]},
               {"kind": "unit", "name": "VILLAGER_MALE", "player": 1, "uuid": "v", "tile": [7.5, 7.5]},
               {"kind": "unit", "name": "MILITIA", "player": 1, "uuid": "m", "tile": [9.5, 9.5]}]
    server = FakeServer({"v": {"Pos": (7.5, 64.0, 7.5)}, "m": {"Pos": (9.5, 64.0, 9.5)}})
    g = gather.Gather(server, grid([[64] * 16 for _ in range(16)], objects)).setup()
    g.stock.update(food=food, gold=gold)
    return server, g


def menus(server):
    return [unquote(c) for c in server.log if c.startswith("aoe menu ")]


def test_the_town_center_menu_has_loom():
    server, g = setup()
    train.open_menu(g, "Steve", (3, 3))
    assert menus(server) == ["aoe menu Steve Town Center 0:villager_spawn_egg:Villager:50 food · 25 s · queue 0/15 "
                             "1:book:Loom:50 gold · 25 s · research" + FEUDAL]


def test_a_click_queues_loom_once_and_takes_its_cost():
    server, g = setup(gold=500)
    rect = train.open_menu(g, "Steve", (3, 3))
    assert train.order(g, "Steve", rect, 1, shift=True) == 1 and g.stock["gold"] == 450
    assert train.order(g, "Steve", rect, 1) == 0 and g.stock["gold"] == 450
    assert menus(server)[-1].endswith("1:book:Loom:50 gold · 25 s · researching" + FEUDAL)


def test_loom_needs_no_population_room_and_changes_the_villagers():
    server, g = setup()
    rect = train.open_menu(g, "Steve", (3, 3))
    g.pop = 99                                                         # above the limit of one town center
    train.order(g, "Steve", rect, 1)
    train.tick(g, 24)
    assert not g.techs and not [c for c in server.log if c.startswith("aoe stats")]
    train.tick(g, 1)
    assert g.techs == {"LOOM"} and not any(g.queues.values())
    s = train.stats(g, "VILLAGER_MALE")
    assert (s.hp, s.melee, s.pierce) == (40, 1, 2) == (25 + 15, 0 + 1, 0 + 2) and train.stats(g, "MILITIA") == combat.stats("MILITIA")
    assert [c for c in server.log if c.startswith("aoe stats")] == ["aoe stats v 40 3 1 2 0 - -"]
    assert any("Loom is researched." in c for c in server.log if c.startswith("tellraw"))
    train.open_menu(g, "Steve", (3, 3))
    assert "Loom" not in menus(server)[-1]
    assert train.queue(g, "Steve", (3, 3), "LOOM") is None             # only once


def test_a_new_villager_has_the_loom_values():
    server, g = setup(food=50)
    g.techs.add("LOOM")
    train.queue(g, "Steve", (3, 3))
    v, = train.tick(g, 25)
    assert f"aoe stats {v.uuid} 40 3 1 2 0 - -" in server.log
