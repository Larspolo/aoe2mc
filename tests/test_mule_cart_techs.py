"""game/train.py: an Armenian or Georgian player researches the lumber camp and mining camp technologies at the mule
cart, as in AoE2 DE (AoE2 wiki "Mule Cart": "Research technologies", #2208). The mining camp items are in the slots right
of the lumber camp items."""
from urllib.parse import unquote

from menu_line import item, labels, order
from test_gather import FakeServer, grid

from game import gather, train


def setup(civ="ARMENIANS"):
    """A flat 16 × 16 map (tile size 1): a mule cart of player 1 (civ) at blocks x 2-3, z 2-3 and a villager."""
    objects = [{"kind": "building", "name": "MULE_CART", "player": 1, "tile": [3.0, 3.0], "footprint": [2, 2, 4, 4]},
               {"kind": "unit", "name": "VILLAGER_MALE", "player": 1, "uuid": "v", "tile": [7.5, 7.5]}]
    server = FakeServer({"v": {"Pos": (7.5, 64.0, 7.5)}})
    g = gather.Gather(server, grid([[64] * 16 for _ in range(16)], objects)).setup()
    g.data["players"] = {"1": {"civ": civ}}
    g.stock.update(food=1000, wood=1000)
    g.techs.add("FEUDAL_AGE")
    return server, g


def menus(server):
    return [unquote(c) for c in server.log if c.startswith("aoe menu ")]


def test_the_mule_cart_menu_has_the_lumber_and_mining_camp_technologies():
    server, g = setup()
    assert train.open_menu(g, "Steve", (2, 3)) == (2, 4, 2, 4)
    cmd, = menus(server)
    assert cmd.startswith("aoe menu Steve Mule Cart ") and labels(cmd) == order(g, "MULE_CART")   # the full menu
    assert item(cmd, "Double-Bit Axe").endswith(" · research") and item(cmd, "Gold Mining").endswith(" · research")
    assert len({s for s, _ in labels(cmd)}) == len(labels(cmd))   # one item per slot


def test_an_armenian_researches_double_bit_axe_and_gold_mining_at_the_mule_cart():
    server, g = setup()
    before = {r: g.work_time(r) for r in ("wood", "gold", "stone")}
    rect = train.open_menu(g, "Steve", (3, 3))
    techs = ("DOUBLE_BIT_AXE", "GOLD_MINING")
    cost = [train.price(g, t, "MULE_CART") for t in techs]
    assert all(train.order(g, "Steve", rect, train.slots("MULE_CART", t)[0]) == 1 for t in techs)
    assert (g.stock["food"], g.stock["wood"]) == tuple(1000 - sum(c.get(r, 0) for c in cost) for r in ("food", "wood"))
    for _ in range(int(sum(train.seconds(g, t, "MULE_CART") for t in techs)) + 1):
        train.tick(g, 1)                                               # one queue: one technology after the other
    assert set(techs) <= g.techs and "STONE_MINING" not in g.techs
    assert g.work_time("wood") < before["wood"] and g.work_time("gold") < before["gold"]
    assert g.work_time("stone") == before["stone"]


def test_the_lumber_and_mining_camp_menus_keep_their_slots():
    first, second = train.MENUS["MULE_CART"]                           # the lumber camp, then the mining camp
    shift = 1 + max(train.SLOTS[n] for n in train.TRAINS[first])
    for n in train.TRAINS[first]:
        assert train.slots("MULE_CART", n)[0] == train.slots(first, n)[0] == train.SLOTS[n], n
    for n in train.TRAINS[second]:                                     # right of the lumber camp items
        assert train.slots("MULE_CART", n)[0] == train.slots(second, n)[0] + shift == train.SLOTS[n] + shift, n
