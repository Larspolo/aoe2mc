"""game/bot.py: with its villager number and a barracks, the bot moves villagers to the resources of its army
(#1049). Fake server of test_gather, the map of test_bot_train."""
import pytest
from test_bot_train import with_buildings

from game import bot, gather


def work(b):
    out = {r: 0 for r in bot.SHARE}
    for v in b.g.villagers.values():
        if v.state != "idle":
            out[v.res] += 1
    return out


def test_the_shares_follow_the_cost_of_the_army():
    server, me, b = with_buildings("HOUSE", "BARRACKS")
    assert b.shares() == bot.SHARE                                     # 5 villagers, the number is 20
    b.villagers = 5
    share, cost = b.shares(), bot.train.price(b.g, "MILITIA")         # the army: militia
    assert share["stone"] == 0 and share["wood"] == bot.WOOD
    assert share["food"] == pytest.approx(cost["food"] / cost["gold"] * share["gold"]) and sum(share.values()) == pytest.approx(1)


def test_no_army_shares_without_a_military_building():
    server, me, b = with_buildings("HOUSE")
    b.villagers = 5
    assert b.shares() == bot.SHARE


def test_the_bot_moves_villagers_from_stone_to_food():
    server, me, b = with_buildings("HOUSE", "BARRACKS")
    for i in range(5, 20):                                             # 20 villagers next to the town center
        pos = (24.5, 64.0, 19.5 + i % 5)
        server.entities[f"b{i}"] = {"Pos": pos}
        b.g.villagers[f"b{i}"] = gather.Villager(f"b{i}", pos)
    b.g.map.bushes.update({t: 10000 for t in b.g.map.bushes})          # food for all the test
    b.villagers = 99                                                   # first the shares of SHARE
    for _ in range(5):
        b.step()
    before = work(b)
    assert len(b.g.villagers) == 20 and before["stone"] == 2 and before["food"] == 8, before
    b.villagers = 20                                                   # the villager number: army shares
    b.step()
    one = work(b)
    assert one["stone"] + one["wood"] == before["stone"] + before["wood"] - 1 and one["food"] == before["food"] + 1
    for _ in range(20):
        b.step()
    after = work(b)
    assert after["stone"] == 0 and after["food"] == 11 and after["gold"] == 5 and after["wood"] == 4, after
