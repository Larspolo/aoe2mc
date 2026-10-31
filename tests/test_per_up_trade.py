"""game/per.py: the UserPatch trade, tribute and escrow commands of AI scripts (up-buy-commodity, up-sell-commodity,
up-tribute-to-player, up-modify-escrow, up-release-escrow, #4871). Each action runs with a constant (c:) and a goal (g:)."""
import diplomacy
import market
from test_per_market import with_market
from test_per_rules import run

GOAL = "(defrule (true) => (set-goal 1 {value}) (disable-self))"


def trade(action, value_kind, value, res="food", **stock):
    """One rule: the goal 1 holds the value (for g:), then the action runs once."""
    text = GOAL.format(value=value) + f"\n(defrule (true) => ({action} {res} {value_kind} {'1' if value_kind == 'g:' else value}) (disable-self))"
    return with_market(text, **stock)


def test_up_sell_commodity_does_value_trades_with_c_and_g():
    s, b, _ = trade("up-sell-commodity", "c:", 2, food=1000, gold=0)
    assert b.g.stock["food"] == 800
    s, b, _ = trade("up-sell-commodity", "g:", 2, food=1000, gold=0)
    assert b.g.stock["food"] == 800


def test_up_buy_commodity_does_value_trades_with_c_and_g():
    stone = dict(gold=1000, stone=0)
    s, b, _ = trade("up-buy-commodity", "c:", 1, "stone", **stone)
    assert b.g.stock["stone"] == market.LOT
    s, b, _ = trade("up-buy-commodity", "g:", 1, "stone", **stone)
    assert b.g.stock["stone"] == market.LOT


def test_up_sell_commodity_stops_at_the_first_failed_trade():
    s, b, _ = trade("up-sell-commodity", "c:", 3, food=150, gold=0)
    assert b.g.stock["food"] == 150 - market.LOT                     # the second trade has too little food


def test_up_tribute_to_player_with_c_and_g():
    s, b, _ = with_market("(defrule (true) => (up-tribute-to-player 1 gold c: 200) (disable-self))", gold=1000)
    assert b.g.stock["gold"] == 1000 - 2 * diplomacy.cost(b.g, 100)  # 200 is two tributes of 100
    s, b, _ = with_market(GOAL.format(value=200) + "\n(defrule (true) => (up-tribute-to-player 1 gold g: 1) (disable-self))",
                          gold=1000)
    assert b.g.stock["gold"] == 1000 - 2 * diplomacy.cost(b.g, 100)


def test_up_modify_escrow_with_c_and_g_stays_between_0_and_the_stock():
    s, b, _ = run("(defrule (true) => (up-modify-escrow food c:+ 50) (disable-self))", food=1000)
    assert s.escrow["food"] == 50
    s, b, _ = run("(defrule (true) => (up-modify-escrow food c:+ 5000) (disable-self))", food=1000)
    assert s.escrow["food"] == 1000                                   # never more than the stock
    s, b, _ = run(GOAL.format(value=30) + "\n(defrule (true) => (up-modify-escrow food g:+ 1) (disable-self))", food=1000)
    assert s.escrow["food"] == 30                                     # the goal 1 is 30, and it adds to 0


def test_up_release_escrow_clears_the_escrow():
    s, b, _ = run("(defrule (true) => (up-release-escrow) (disable-self))", steps=0, food=1000)
    s.escrow.update(food=50, gold=20)
    s.step()
    assert s.escrow == {}
