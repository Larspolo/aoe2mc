"""game/civs.py LAST: the resources of Mayan players last longer, Puru stone mines too, and Tatar herdables have more food
(AoE2 DE civilization bonuses, #2112). The factors come from civs.LAST."""
import math

from test_gather import FakeServer, grid

from game import civs, gather


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


BASE = next(r["name"] for r in civs.ROWS if r["name"] not in civs.LAST)   # a civilization with no bonus
KINDS = (("TREE_OAK", "wood"), ("FRUIT_BUSH", "food"), ("GOLD_MINE", "gold"), ("STONE_MINE", "stone"))


def lasts(civ, amount, kind):
    """The loads of an amount of kind for civ: one take is 1 / factor (Gather.step)."""
    return math.ceil(amount * civs.LAST.get(civ, {}).get(kind, 1) - 1e-6)


def test_mayan_resources_last_longer():
    for obj, kind in KINDS:
        amount = gathered(BASE, obj)
        assert gathered("MAYANS", obj) == lasts("MAYANS", amount, kind), obj
    assert gathered("MAYANS", carcass=(100, False)) == lasts("MAYANS", 100, "hunt")    # a deer
    assert gathered("MAYANS", carcass=(100, True)) == lasts("MAYANS", 100, "sheep")    # a sheep


def test_puru_stone_mines_last_longer():
    for obj, kind in KINDS[::2] + KINDS[3:]:
        assert gathered("PURU", obj) == lasts("PURU", gathered(BASE, obj), kind), obj


def test_tatar_herdables_have_more_food():
    assert gathered("TATARS", carcass=(100, True)) == lasts("TATARS", 100, "sheep")
    assert gathered("TATARS", carcass=(100, False)) == lasts("TATARS", 100, "hunt")    # a deer is not a herdable
    assert gathered(BASE, carcass=(100, True)) == 100


def test_a_civilization_with_no_bonus_lasts_as_in_aoe2():
    g = type("G", (), {"data": {"players": {"1": {"civ": BASE}}}, "player": 1})()
    assert civs.last(g, "wood") == 1
    assert gathered(BASE, "TREE_OAK") == gather.TREE_WOOD and gathered(BASE, "FRUIT_BUSH") == gather.BUSH_FOOD
