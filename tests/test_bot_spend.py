"""game/bot.py: a bot researches its technologies before it trains more soldiers, and moves its villagers off a
resource with a large stock (#4285). Fake server of test_gather, the map of test_bot_gather."""
import pytest
from test_bot_keep_age import ready
from test_bot_research import queued
from test_bot_train import with_buildings

from game import bot

build, train = bot.build, bot.train


def test_an_economy_technology_gets_the_food_before_a_soldier(monkeypatch):
    missing = next(n for n in bot.ORDER if n not in ("BARRACKS", "LUMBER_CAMP")
                   and any(r["name"] == n and r.get("age") == 1 for r in build.ROWS))
    b = ready(monkeypatch, [n for n in bot.ORDER if n != missing])
    b.g.techs.add(build.AGE_TECHS[0])
    b.g.sites.append({"name": "LUMBER_CAMP", "player": 2, "footprint": [26, 28, 20, 22], "done": True})
    keep, cost = b.keep(), train.price(b.g, "DOUBLE_BIT_AXE")
    assert keep == build.price(b.g, missing)                           # the age waits for the missing building
    b.g.stock.update({r: cost.get(r, 0) + keep.get(r, 0) for r in b.g.stock} | {"gold": 500})
    assert b.soldiers("BARRACKS")                                      # the barracks could take the food
    b.spend()
    assert queued(b) == ["DOUBLE_BIT_AXE"]


def test_a_resource_with_a_large_stock_gets_no_villagers():
    server, me, b = with_buildings("HOUSE", "BARRACKS")
    b.villagers = len(b.g.villagers)                                   # the army shares
    before = b.shares()
    b.g.stock["gold"] = b.needs(b.army()).get("gold", 0) + bot.SPARE
    share = b.shares()
    assert before["gold"] > 0 and share["gold"] == 0 and sum(share.values()) == pytest.approx(1)
    assert share["food"] > before["food"] and share["wood"] > before["wood"]
