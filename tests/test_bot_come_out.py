"""game/bot.py: the villagers of a bot go back to work after they come out of a building (#3543)."""
from test_bot_gather import bot_map

from game import bot


def test_villagers_that_come_out_idle_gather_again():
    server, me, b = bot_map()
    for _ in range(60):
        b.step()
    stone = {u for u, v in b.g.villagers.items() if v.res == "stone"}
    for v in b.g.villagers.values():
        v.state = "garrison"                                           # the town bell: in (garrison.go)
    b.orders()
    for v in b.g.villagers.values():
        v.state = "idle"                                               # out, v.tree kept (garrison.out)
    b.orders()
    assert not b.failed
    assert all(v.state != "idle" for v in b.g.villagers.values())
    assert stone and all(b.g.villagers[u].res == "stone" for u in stone)


def test_a_source_without_a_path_is_tried_again_after_a_while():
    server, me, b = bot_map()
    b.step()
    v = next(v for v in b.g.villagers.values() if v.res == "stone")
    stone = v.tree
    b.g.set(v, "idle")                                                 # it found no path to the mine
    b.step()
    assert stone in b.failed and v.tree != stone
    b.time += bot.RETRY
    assert b.go(v, "stone") and b.sent[v.uuid] == stone
