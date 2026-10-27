"""game/bot.py: with the army shares and no free farm, the bot moves its gold and stone villagers above their share
to wood, the cost of the next farm (#1083). Fake server of test_gather, the map of test_bot_train."""
from test_bot_army_share import work
from test_bot_train import with_buildings

from game import gather


def test_villagers_leave_stone_for_wood_when_no_farm_is_free():
    server, me, b = with_buildings("HOUSE", "BARRACKS")
    for i in range(5, 20):                                             # 20 villagers next to the town center
        pos = (24.5, 64.0, 19.5 + i % 5)
        server.entities[f"b{i}"] = {"Pos": pos}
        b.g.villagers[f"b{i}"] = gather.Villager(f"b{i}", pos)
    b.villagers = 99                                                   # first the shares of SHARE
    for _ in range(5):
        b.step()
    before = work(b)
    assert len(b.g.villagers) == 20 and before["stone"] >= 2, before
    b.g.map.bushes.update({t: 0 for t in b.g.map.bushes})              # no food left, no farm
    b.villagers = 20                                                   # the villager number: army shares
    for _ in range(20):
        b.step()
    after = work(b)
    assert after["stone"] == 0 and after["gold"] == 5, after
    assert after["wood"] + after["food"] == 15, after
