"""tools/play_check.py: the driver of player 1 trains soldiers while its town bell rings and in a raid while it saves
for an age, and its villagers gather the price of the age (#3561)."""
from test_bot_gather import bot_map
from test_play_check import ready

import play_check
from game import bot


def driver():
    """bot_map with a barracks and 3 houses of player 1, and the driver of player 1."""
    server, me, b = bot_map()
    for name, box in (("BARRACKS", [14, 24, 17, 27]), ("HOUSE", [24, 24, 26, 26]), ("HOUSE", [27, 24, 29, 26]),
                      ("HOUSE", [24, 27, 26, 29])):
        me.data["objects"].append({"kind": "building", "name": name, "player": 1, "footprint": box})
    return server, me, b, play_check.Driver(me, b.g)


def queued(me):
    return sorted(e["name"] for q in me.queues.values() for e in q)


def test_with_the_bell_rung_the_driver_queues_soldiers_and_no_villager():
    server, me, b, d = driver()
    me.stock.update(food=1000, wood=1000, gold=1000)
    d.rung, d.looked = (2, 6, 2, 6), d.time                            # rung; no new look in this step
    d.orders()
    assert queued(me) == ["MILITIA"] * bot.QUEUED


def test_while_it_saves_the_driver_trains_soldiers_only_in_a_raid():
    server, me, b, d = driver()
    ready(me)
    me.stock.update(food=400, wood=1000, gold=1000)
    d.advance()
    assert d.saving == "FEUDAL_AGE"
    d.recruit()
    assert queued(me) == []
    d.foes = {"b0": (5.5, 64.0, 5.5)}
    d.recruit()
    assert queued(me) == ["MILITIA"] * bot.QUEUED


def test_while_it_saves_for_the_feudal_age_food_has_the_largest_share():
    server, me, b, d = driver()
    ready(me)
    me.stock.update(food=0, wood=0, gold=0, stone=0)
    d.advance()
    share = d.shares()
    assert d.saving == "FEUDAL_AGE" and max(share, key=share.get) == "food" and abs(sum(share.values()) - 1) < 1e-9


def test_the_result_names_the_times_of_the_bell():
    r = {"end": "time", "time": "40:00", "players": {}, "stuck": [], "errors": [], "bells": ["17:29-18:10"]}
    assert "Town bell of player 1 (game time): 17:29-18:10." in play_check.report(r)
