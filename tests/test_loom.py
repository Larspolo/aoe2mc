"""game/train.py: the town center menu has "Loom" (a book). A click queues it once; after the research the villagers
have more hit points and armor, and the item leaves the menu (#655)."""
from urllib.parse import unquote

import lang
from menu_line import item
from test_gather import FakeServer, grid

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
    """The menu commands of the log; a long menu with its `aoe menu-add` parts as one text (#1647, #2483)."""
    out = []
    for c in server.log:
        if c.startswith("aoe menu "):
            out.append(unquote(c))
        elif c.startswith("aoe menu-add ") and out:
            out[-1] += " " + unquote(c.split(" ", 4)[4])
    return out


def test_the_town_center_menu_has_loom():
    server, g = setup()
    train.open_menu(g, "Steve", (3, 3))
    assert len(menus(server)) == 1 and item(menus(server)[0], "Loom").split(":")[1] == "book"
    assert item(menus(server)[0], "Loom").endswith(" · research")


def test_a_click_queues_loom_once_and_takes_its_cost():
    server, g = setup(gold=500)
    rect = train.open_menu(g, "Steve", (3, 3))
    gold, slot = 500 - train.price(g, "LOOM")["gold"], train.SLOTS["LOOM"]
    assert train.order(g, "Steve", rect, slot, shift=True) == 1 and g.stock["gold"] == gold
    assert train.order(g, "Steve", rect, slot) == 0 and g.stock["gold"] == gold
    assert item(menus(server)[-1], "Loom").endswith(" · researching")


def test_loom_needs_no_population_room_and_changes_the_villagers():
    server, g = setup(gold=5000)
    rect = train.open_menu(g, "Steve", (3, 3))
    g.pop = 99                                                         # above the limit of one town center
    train.order(g, "Steve", rect, train.SLOTS["LOOM"])
    train.tick(g, train.seconds(g, "LOOM", "TOWN_CENTER") - 1)
    assert not g.techs and not [c for c in server.log if c.startswith("aoe stats")]
    train.tick(g, 1)
    assert g.techs == {"LOOM"} and not any(g.queues.values())
    s, old = train.stats(g, "VILLAGER_MALE"), combat.stats("VILLAGER_MALE")
    assert s.hp > old.hp and s.melee > old.melee and s.pierce > old.pierce
    assert train.stats(g, "MILITIA") == combat.stats("MILITIA")
    assert [c for c in server.log if c.startswith("aoe stats")] == [combat.stats_command("v", "VILLAGER_MALE", s)]
    assert any("Loom is researched." in c for c in map(lang.english, server.log) if c.startswith("tellraw"))
    train.open_menu(g, "Steve", (3, 3))
    assert "Loom" not in menus(server)[-1]
    assert train.queue(g, "Steve", (3, 3), "LOOM") is None             # only once


def test_a_new_villager_has_the_loom_values():
    server, g = setup(food=5000)
    g.techs.add("LOOM")
    train.queue(g, "Steve", (3, 3))
    v, = train.tick(g, train.seconds(g, "VILLAGER_MALE", "TOWN_CENTER"))
    assert combat.stats_command(v.uuid, "VILLAGER_MALE", train.stats(g, "VILLAGER_MALE")) in server.log
    assert train.stats(g, "VILLAGER_MALE").hp > combat.stats("VILLAGER_MALE").hp
