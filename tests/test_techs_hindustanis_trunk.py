"""The unique technology of the Hindustanis in the Castle Age (#4324): the castle of the Hindustanis researches Grand
Trunk Road, with the values of the AoE2 DE wiki ("Unique technology"): more gold from gold mines, trade and relics
(the keys "work" and "gold_rate" of data/train.jsonl) and a lower trading fee (the key "fee")."""
import pytest
from test_free_relic import church
from test_techs_persians import label
from test_trade_cart import FAR, HOME, moves, setup as trade_setup
from test_train_castle import menus, setup
from test_treadmill_crane import castle

from game import gather, market, monk, trade, train

NAME, CASTLE = "GRAND_TRUNK_ROAD", (12, 4)


def test_only_the_castle_of_the_hindustanis_researches_grand_trunk_road():
    server, g = setup("HINDUSTANIS")
    train.open_menu(g, "Steve", CASTLE)
    assert f":{label(g, NAME)}:" in menus(server)[-1]
    server, g = setup("BRITONS")
    train.open_menu(g, "Steve", CASTLE)
    assert label(g, NAME) is None


def test_grand_trunk_road_lowers_the_fee_and_mines_gold_faster():
    _, g = setup("HINDUSTANIS")
    before = g.work_time("gold")
    assert market.fee(g) == market.FEE
    g.techs.add(NAME)
    assert market.fee(g) == train.value("fee", NAME) < market.FEE
    assert g.work_time("gold") == pytest.approx(before / gather.WORK_TECHS[NAME]["gold"])


def relic_gold(techs):
    _, g = castle("ARMENIANS")
    church(g, (12, 15, 8, 11))
    g.techs |= techs
    gold = g.stock["gold"]
    for _ in range(60):
        monk.relic_tick(g, monk.EVERY)
    return g.stock["gold"] - gold


def test_grand_trunk_road_gives_more_relic_gold():
    assert relic_gold({NAME}) == round(relic_gold(set()) * train.value("gold_rate", NAME))


def trip_gold(techs):
    server, g = trade_setup()
    g.techs |= techs
    g.selected = {"c"}
    assert trade.order(g, "Steve", (19, 17)) == FAR
    server.entities["c"]["Pos"] = moves(server, "c")[-1]           # at the far market
    trade.tick(g)
    server.entities["c"]["Pos"] = moves(server, "c")[-1]           # at home: the gold of one trip
    trade.tick(g)
    return g.stock["gold"] + g.trade["c"]["rest"]


def test_grand_trunk_road_gives_more_trade_gold():
    assert trip_gold({NAME}) == pytest.approx(trip_gold(set()) * train.value("gold_rate", NAME))
    assert trip_gold(set()) == pytest.approx(trade.gold(trade.center(HOME, 1), trade.center(FAR, 1), 24))
