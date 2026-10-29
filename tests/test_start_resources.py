"""The players of the game program start with the AoE2 standard resources (#973): gather.START. The map and fake server of test_bot_gather (the check #964 found a bot that started at 0)."""
import test_bot_gather
from test_gather import FakeServer, grid

from game import bot, gather, replay


def start_map(start=None):
    """bot_map of test_bot_gather with a forest of 12 more trees (as on the map of #964), the AoE2 rates and the
    given start of both players."""
    server, me, _ = test_bot_gather.bot_map()
    me.data["objects"] += [{"kind": "other", "name": "TREE_OAK", "tile": [x + 0.5, z + 0.5]}
                           for x in (26, 27, 28) for z in (23, 24, 25, 26)]
    kw = {} if start is None else {"start": start}
    me = gather.Gather(server, me.data, **kw).setup()
    return server, me, bot.Bot(server, me.data, share=me, **kw).setup()


def test_a_new_gather_has_the_start_resources_and_the_sidebar_shows_them():
    server = FakeServer({})
    g = gather.Gather(server, grid([[64] * 8 for _ in range(8)], [])).setup()
    start = dict(gather.START)
    assert g.stock == start
    for r in ("Wood", "Food", "Gold", "Stone"):
        assert f"scoreboard players set {r} aoe_res {gather.START[r.lower()]}" in server.log
    g.stock["wood"] -= 25                                              # a copy: START stays
    assert gather.START == start and gather.Gather(server, g.data, start={}).stock["wood"] == 0


def test_the_replay_uses_the_same_start():
    assert replay.START == gather.START


def test_the_bot_builds_a_house_at_once_and_a_barracks_before_10_minutes():
    server, me, b = start_map()
    b.g.aegis = True                                                   # instant building: the order, not the speed
    b.g.pop = 3                                                        # town center: limit 5, a house at 3
    b.step()
    assert [s["name"] for s in b.g.sites] == ["HOUSE"]                 # at once: no wait for 25 wood
    for _ in range(int(600 / b.g.tick)):                               # 10:00 of game time
        b.step()
        if "BARRACKS" in bot.train.owned(b.g):
            break
    assert "BARRACKS" in bot.train.owned(b.g), [s["name"] for s in b.g.sites]
