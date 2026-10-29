"""game/bot.py: a bot researches the economy technologies of all buildings before the others (#4206). Fake server of
test_gather, the map of test_bot_gather."""
from test_bot_research import queued
from test_bot_smith import smith

from game import bot

train = bot.train


def test_the_economy_technology_of_a_later_building_comes_before_a_blacksmith_technology():
    b = smith(["ARCHER"])
    keep, prices = b.keep(), [train.price(b.g, n) for n in ("DOUBLE_BIT_AXE", "FLETCHING")]
    b.g.stock.update({r: max(p.get(r, 0) for p in prices) + keep.get(r, 0) for r in b.g.stock})  # one of the two
    b.research()
    assert queued(b) == ["DOUBLE_BIT_AXE"]
    assert queued(b, "BLACKSMITH") == []
