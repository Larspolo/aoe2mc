"""game/per.py: the airef form of the UserPatch trade actions, with a typeOp before the resource (#5090):
(up-buy-commodity c: stone c: 2). The present form (up-sell-commodity food c: 2) stays in test_per_up_trade.py."""
import market
from test_per_market import with_market

GOAL = "(defrule (true) => (set-goal 1 {value}) (disable-self))"


def trade(action, res_kind, res, value_kind, value, **stock):
    """One rule: the goal 1 holds the value (for g:), then the action runs once."""
    text = GOAL.format(value=value) + f"\n(defrule (true) => ({action} {res_kind} {res} {value_kind} {'1' if value_kind == 'g:' else value}) (disable-self))"
    return with_market(text, **stock)


def test_up_buy_commodity_with_typed_resource_does_value_trades():
    s, b, _ = trade("up-buy-commodity", "c:", "stone", "c:", 2, gold=1000, stone=0)
    assert b.g.stock["stone"] == 2 * market.LOT


def test_up_sell_commodity_with_typed_resource_and_goal_does_value_trades():
    s, b, _ = trade("up-sell-commodity", "c:", "food", "g:", 1, food=1000, gold=0)
    assert b.g.stock["food"] == 1000 - market.LOT
