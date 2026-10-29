"""game/train.py and game/gather.py: the town center menu has "Wheelbarrow" from the Feudal Age, with its values of
game/data/train.jsonl. After the research the villagers carry more resources and walk faster, as in AoE2 (#728)."""
from urllib.parse import unquote

from menu_line import item
from test_gather import FakeServer, grid, tiny
from test_urumi_swordsman import item as text

from game import ai, gather, train

NAME = train.ITEMS["WHEELBARROW"][2]
COST = train.COSTS["WHEELBARROW"]


def setup(food=175, wood=50):
    """A flat 16 × 16 map (tile size 1): a town center of player 1 at blocks x 2-4, z 2-4 and a villager."""
    objects = [{"kind": "building", "name": "TOWN_CENTER", "player": 1, "tile": [3.5, 3.5], "footprint": [2, 2, 5, 5]},
               {"kind": "unit", "name": "VILLAGER_MALE", "player": 1, "uuid": "v", "tile": [7.5, 7.5]}]
    server = FakeServer({"v": {"Pos": (7.5, 64.0, 7.5)}})
    g = gather.Gather(server, grid([[64] * 16 for _ in range(16)], objects)).setup()
    g.stock.update(food=food, wood=wood)
    g.techs.add("FEUDAL_AGE")
    return server, g


def menus(server):
    return [unquote(c) for c in server.log if c.startswith("aoe menu ")]


def test_no_wheelbarrow_in_the_dark_age():
    server, g = setup(food=1000, wood=1000)
    g.techs.clear()
    train.open_menu(g, "Steve", (3, 3))
    assert NAME not in menus(server)[-1] and train.queue(g, "Steve", (3, 3), "WHEELBARROW") is None
    assert g.stock["food"] == 1000


def test_the_town_center_menu_has_wheelbarrow():
    server, g = setup(food=1000, wood=1000)
    train.open_menu(g, "Steve", (3, 3))
    assert f" {item(menus(server)[-1], NAME)} " == text(g, "WHEELBARROW", "research")


def test_a_click_queues_wheelbarrow_once_and_takes_its_cost():
    server, g = setup(food=1000, wood=1000)
    rect = train.open_menu(g, "Steve", (3, 3))
    slot = train.ITEMS["WHEELBARROW"][0]
    food, wood = 1000 - COST.get("food", 0), 1000 - COST.get("wood", 0)
    assert train.order(g, "Steve", rect, slot, shift=True) == 1 and (g.stock["food"], g.stock["wood"]) == (food, wood)
    assert train.order(g, "Steve", rect, slot) == 0 and g.stock["food"] == food
    assert f" {item(menus(server)[-1], NAME)} " == text(g, "WHEELBARROW", "researching")


def test_wheelbarrow_gives_more_carry_after_its_time():
    server, g = setup(food=1000, wood=1000)
    rect = train.open_menu(g, "Steve", (3, 3))
    train.order(g, "Steve", rect, train.ITEMS["WHEELBARROW"][0])
    seconds, carry = train.seconds(g, "WHEELBARROW"), g.limit()
    train.tick(g, seconds - 1)
    assert g.techs == {"FEUDAL_AGE"} and g.limit() == carry
    train.tick(g, 1)
    assert g.techs == {"FEUDAL_AGE", "WHEELBARROW"} and g.limit() > carry and not any(g.queues.values())
    assert any(f"{NAME} is researched." in c for c in server.log if c.startswith("tellraw"))
    assert not [c for c in server.log if c.startswith("aoe stats")]   # no combat change
    train.open_menu(g, "Steve", (3, 3))
    assert NAME not in menus(server)[-1]


def test_a_villager_walks_faster_on_paper():
    server, g = setup()
    v = g.villagers["v"]
    v.goal = (10, 10)
    g.move(v)
    g.techs.add("WHEELBARROW")
    g.move(v)
    before, after = [c for c in server.log if c.startswith("attribute v minecraft:movement_speed")]
    factor = train.speed(g, "VILLAGER", "v") * gather.PACE["WHEELBARROW"]   # the walk factor of the data
    assert factor > 1 and before == ai.speed_command("v", "VILLAGER", 1)
    assert after == ai.speed_command("v", "VILLAGER", 1, gather.NORMAL * factor)
    assert ai.walk_speed("VILLAGER", 1, gather.NORMAL * 1.1) == 1.1 * ai.walk_speed("VILLAGER", 1)


def test_a_villager_drops_more_wood_after_wheelbarrow(tiny_world):
    data, uuid, _, _ = tiny(tiny_world)
    server = FakeServer({uuid: {"Pos": (0.0, 0.0, 0.0)}})
    g = gather.Gather(server, data, tick=0.25, carry=10, chop=0.25).setup()
    g.techs.add("WHEELBARROW")
    tree, = g.map.trees
    g.select(uuid)
    g.send(tree)
    for _ in range(400):
        g.step()
        if server.wood():
            break
    assert server.wood() == g.limit("wood") > 10
