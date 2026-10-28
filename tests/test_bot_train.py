"""game/bot.py: the bot of player 2 trains villagers up to a number, then soldiers at its barracks (#858)."""
from test_bot_gather import bot_map

from game import bot, train


def with_buildings(*names):
    """bot_map with more complete buildings of player 2 (3 houses: room for 20 units)."""
    server, me, b = bot_map()
    spots = {"HOUSE": [[24, 24, 26, 26], [27, 24, 29, 26], [24, 27, 26, 29]], "BARRACKS": [[14, 24, 17, 27]]}
    for name in names:
        b.g.data["objects"].append({"kind": "building", "name": name, "player": 2, "footprint": spots[name].pop(0)})
    return server, me, b


def test_the_bot_keeps_two_villagers_in_the_queue_of_its_town_center():
    server, me, b = with_buildings("HOUSE", "HOUSE", "HOUSE")
    b.g.stock["food"] = 1000
    before = len(server.log)
    b.recruit()
    (q,) = b.g.queues.values()
    assert [e["name"] for e in q] == ["VILLAGER_MALE"] * bot.QUEUED and b.g.stock["food"] == 1000 - 50 * bot.QUEUED
    assert not [c for c in server.log[before:] if "aoe_res" in c.split()]      # the resources of the bot, not of player 1


def test_the_bot_trains_villagers_up_to_its_number():
    server, me, b = with_buildings("HOUSE", "HOUSE", "HOUSE")
    b.villagers = 8
    b.g.stock["food"] = 1000
    for _ in range(2000):
        b.step()
    assert len(b.g.villagers) == 8 and not any(b.g.queues.values())   # 5 at the start, 3 trained
    assert b.g.stock["food"] >= 1000 - 3 * 50


def test_the_bot_trains_soldiers_at_its_barracks():
    server, me, b = with_buildings("HOUSE", "BARRACKS")
    b.villagers = 5                                                    # no more villagers
    b.g.stock.update(food=600, gold=200)
    for _ in range(600):
        b.step()
    assert len(b.g.soldiers) >= 2 and set(b.g.soldiers.values()) == {"MILITIA"}
    assert all(c["name"] == "MILITIA" for q in b.g.queues.values() for c in q)


def test_the_bot_waits_for_the_resources():
    server, me, b = with_buildings("HOUSE", "BARRACKS")
    b.g.stock.update(food=40, gold=0)
    b.recruit()
    assert not any(b.g.queues.values()) and b.g.stock["food"] == 40
    assert not [c for c in server.log if c.startswith("tellraw")]     # no text for a failed queue
    assert train.homes(b.g)                                            # it has buildings that train
