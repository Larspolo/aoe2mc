"""game/bot.py: the soldiers of a bot leave the cost of its next technology (#4495). Fake server of test_gather, the
map of test_bot_gather."""
from test_bot_smith import smith

from game import bot

train = bot.train


def barracks_bot(stock):
    """A Feudal bot with a Blacksmith, a Barracks, one Militia and stock above keep() (stock: resource -> amount)."""
    b = smith(["MILITIA"])
    b.g.sites.append({"name": "BARRACKS", "player": 2, "footprint": [14, 17, 28, 31], "done": True})
    keep = b.keep()
    b.g.stock.update({r: keep.get(r, 0) + stock.get(r, 0) for r in b.g.stock})
    return b


def soldiers(b):
    return [e["name"] for q in b.g.queues.values() for e in q if e["name"] == "MILITIA"]


def test_the_bot_keeps_the_cost_of_its_next_technology_from_its_soldiers():
    b = barracks_bot(train.price(barracks_bot({}).g, "MILITIA"))       # a Militia, not the next technology
    assert b.wanted()
    b.recruit()
    assert soldiers(b) == []


def test_the_bot_trains_soldiers_with_the_resources_above_the_technology():
    b = barracks_bot({r: 5000 for r in bot.SHARE})
    b.recruit()
    assert soldiers(b)
