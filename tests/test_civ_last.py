"""game/civs.py LAST: the resources of Mayan players last 15 % longer, Puru stone mines 30 % and Tatar herdables have 50 %
more food (AoE2 DE civilization bonuses, #2112)."""
import math

from game import civs, gather

from test_gather import FakeServer, grid


def gathered(civ, obj=None, carcass=None):
    """The resources that one villager of a player of civ gathers from obj (an object name at tile (4, 4)) or from a
    carcass (food, herd) until it is empty: the villager carries all of it, with no drop."""
    objects = [{"kind": "unit", "name": "VILLAGER_MALE", "player": 1, "uuid": "v", "tile": [7.5, 7.5]}]
    objects += [{"kind": "other", "name": obj, "tile": [4.5, 4.5]}] if obj else []
    data = grid([[64] * 16 for _ in range(16)], objects)
    data["players"] = {"1": {"civ": civ, "color": 0}}
    g = gather.Gather(FakeServer({"v": {"Pos": (7.5, 64.0, 7.5)}}), data, carry=10 ** 6, start={}).setup()
    v = g.villagers["v"]
    if carcass:
        food, herd = carcass
        g.map.carcasses[(4, 4)] = food
        if herd:
            g.map.herds.add((4, 4))
        v.res = "food"
    else:
        v.res = next((r for r, m in g.map.mines.items() if m), "food" if (4, 4) in g.map.bushes else "wood")
    v.tree, v.state = (4, 4), "chop"
    src = g.source(v)
    for _ in range(100000):
        if src.get((4, 4), 0) <= 0:
            break
        g.step()
    return v.load


def test_mayan_resources_last_15_percent_longer():
    for obj, amount in (("TREE_OAK", gather.TREE_WOOD), ("FRUIT_BUSH", gather.BUSH_FOOD), ("GOLD_MINE", 800),
                        ("STONE_MINE", 350)):
        assert gathered("GOTHS", obj) == amount
        assert gathered("MAYANS", obj) == math.ceil(amount * 1.15), obj
    assert gathered("MAYANS", carcass=(100, False)) == 115                 # a deer
    assert gathered("MAYANS", carcass=(100, True)) == 115                  # a sheep


def test_puru_stone_mines_last_30_percent_longer():
    assert gathered("PURU", "STONE_MINE") == 455
    assert gathered("PURU", "GOLD_MINE") == 800 and gathered("PURU", "TREE_OAK") == gather.TREE_WOOD


def test_tatar_herdables_have_50_percent_more_food():
    assert gathered("TATARS", carcass=(100, True)) == 150
    assert gathered("TATARS", carcass=(100, False)) == 100                 # a deer is not a herdable
    assert gathered("GOTHS", carcass=(100, True)) == 100


def test_a_civilization_with_no_bonus_lasts_as_in_aoe2():
    g = type("G", (), {"data": {"players": {"1": {"civ": "FRANKS"}}}, "player": 1})()
    assert "FRANKS" not in civs.LAST and civs.last(g, "wood") == 1
