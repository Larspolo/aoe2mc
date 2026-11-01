"""game/bot.py: an army unit with no food in its cost (the Archer) gave food no share, so the bot put no villager on
its free farms and never had the food of the Castle Age or of a new villager (#5559, play check: 15 free farms,
food 35 from 22:00 to 34:00). A resource that the needs lack keeps its share. Map of test_bot_train."""
import pytest
from test_bot_train import with_buildings

from game import bot


def archers(food):
    server, me, b = with_buildings("HOUSE", "BARRACKS")
    b.villagers = len(b.g.villagers)                                   # the army shares
    b.army = lambda: "ARCHER"                                          # its first military building: archery range
    b.keep = lambda: {"food": 800, "gold": 200}                        # the cost of the Castle Age
    b.g.stock.update({"food": food, "gold": 0})
    return b


def test_the_food_of_the_next_age_keeps_a_share_with_an_army_of_archers():
    assert "food" not in bot.train.price(archers(0).g, "ARCHER")
    share = archers(100).shares()
    assert share["food"] > 0 and share["gold"] > 0 and sum(share.values()) == pytest.approx(1)


def test_no_food_share_for_archers_when_the_stock_has_the_food():
    b = archers(0)
    b.g.stock["food"] = b.needs("ARCHER")["food"]                      # the age and the economy technologies
    share = b.shares()
    assert share["food"] == 0 and sum(share.values()) == pytest.approx(1)
