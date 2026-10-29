"""game/fleet.py and game/train.py: an own dock trains the trade cog in the Feudal Age (AoE2 DE wiki
"Trade Cog"), and a trade cog sent to a second own dock sails between the two docks and brings the gold of the
AoE2 trade formula (trade.gold) at each arrival at home (#1485)."""
from test_build_site import Server
from test_gather import grid
from test_train_archery import menus

import units
from game import fleet, gather, trade, train

HOME, FAR = (14, 17, 2, 5), (14, 17, 32, 35)                       # block footprints (x0, x1, z0, z1), tile size 1
TIME = train.TRAIN_TIMES["TRADE_COG"]


def docks_map():
    """A flat 40 x 40 map (tile size 1): land at x < 14, water at x >= 14, two docks of player 1 at the shore."""
    rows = [[64] * 14 + ["-"] * 26 for _ in range(40)]
    dock = lambda r: {"kind": "building", "name": "DOCK", "player": 1, "tile": [15.5, (r[2] + r[3]) / 2],   # noqa: E731
                      "footprint": [r[0], r[2], r[1], r[3]]}
    data = grid(rows, [{"kind": "building", "name": "TOWN_CENTER", "player": 1, "tile": [3.5, 3.5], "footprint": [2, 2, 5, 5]},
                       dock(HOME), dock(FAR)])
    data["players"] = {"1": {"civ": "BRITONS", "color": "blue", "arch": "western"}}
    data["level_height"] = 1
    server = Server({"Steve": {"Pos": (12.5, 64.0, 3.5), "Rotation": (-90.0, 40.0)}})
    g = gather.Gather(server, data).setup()
    g.stock.update(**train.COSTS["TRADE_COG"])
    g.techs = {"FEUDAL_AGE"}
    return server, g


def test_the_dock_trains_it_from_the_item_row_under_the_queue():
    server, g = docks_map()
    g.techs = set()
    train.open_menu(g, "Steve", (15, 3))
    label = train.ITEMS["TRADE_COG"][2]
    assert f"{train.MORE}:{train.build.LOCKED}:{label}:" in menus(server)[-1]
    assert train.order(g, "Steve", HOME, train.MORE) == 0
    g.techs = {"FEUDAL_AGE"}
    train.open_menu(g, "Steve", (15, 3))
    assert f"{train.MORE}:{units.classify('TRADE_COG')['id'].removeprefix('minecraft:')}:{label}:" in menus(server)[-1]
    assert train.order(g, "Steve", HOME, train.MORE) == 1 and not any(g.stock[r] for r in train.COSTS["TRADE_COG"])
    cog, = train.tick(g, TIME)
    assert g.soldiers[cog] == "TRADE_COG" and cog in g.ships


def test_a_trade_cog_sails_between_two_docks_and_brings_gold_at_home():
    server, g = docks_map()
    train.order(g, "Steve", train.open_menu(g, "Steve", (15, 3)), train.MORE)
    cog, = train.tick(g, TIME)
    g.selected = {cog}
    assert fleet.trade_order(g, "Steve", (15, 33)) == FAR
    trip = trade.gold(trade.center(HOME, 1), trade.center(FAR, 1), 40)
    assert 10 < trip < 11                                              # 0.46 * 25 * (25 / 40 + 0.3)
    seen, far = [], False
    for _ in range(200):
        fleet.tick(g, 0.5)
        v = g.ships[cog]
        far |= v.cell in fleet.pier(g, FAR)
        seen.append(g.stock["gold"])
    assert far and g.ships[cog].state == "to_trade"
    trips = g.ships[cog].route["rest"] + g.stock["gold"]
    assert g.stock["gold"] >= int(trip) and abs(trips / trip - round(trips / trip)) < 1e-6   # whole trips, the fraction kept
    assert seen[0] == 0 and seen == sorted(seen)


def test_a_move_order_ends_the_route_and_a_cart_order_does_not_take_a_dock():
    server, g = docks_map()
    train.order(g, "Steve", train.open_menu(g, "Steve", (15, 3)), train.MORE)
    cog, = train.tick(g, TIME)
    g.selected = {cog}
    fleet.trade_order(g, "Steve", (15, 33))
    fleet.order(g, {cog}, (30, 20))
    for _ in range(100):
        fleet.tick(g, 0.5)
    assert g.ships[cog].state == "idle" and g.stock["gold"] == 0
    assert trade.order(g, "Steve", (15, 33)) is None                   # a market order: not a dock


def test_a_right_click_on_the_far_dock_with_a_selected_cog_is_a_trade_order():
    server, g = docks_map()
    train.order(g, "Steve", train.open_menu(g, "Steve", (15, 3)), train.MORE)
    cog, = train.tick(g, TIME)
    g.selected = {cog}
    server.entities["Steve"] = {"Pos": (12.5, 64.0, 33.5), "Rotation": (-90.0, 40.0)}   # look east and down at FAR
    g.click("Steve")
    assert g.ships[cog].route["dock"] == FAR and g.ships[cog].state == "to_trade"
