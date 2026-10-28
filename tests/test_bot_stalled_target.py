"""game/bot.py: a soldier of the bot that comes no nearer to its target and does no damage to it for STALL seconds
takes another target (#3441: 13 to 18 soldiers kept a target that they could not hit and destroyed nothing)."""
import re

from test_bot_attack import armed, orders
from test_bot_water import lake

from game import bot, combat


def healthy(server):
    """The fake server answers the Health of an entity and the score aoe_hp of a building (server.hp)."""
    command = server.command
    server.hp = {}

    def answer(cmd):
        if m := re.fullmatch(r"data get entity (\S+) Health", cmd):
            e = server.entities.get(m[1], {})
            return f"{m[1]} has the following entity data: {e['Health']}f" if "Health" in e else "No entity was found"
        if (m := re.fullmatch(r"scoreboard players get (\S+) aoe_hp", cmd)) and m[1] in server.hp:
            return f"{m[1]} has {server.hp[m[1]]} [aoe_hp]"
        return command(cmd)
    server.command = answer


def setup():
    """Two militia of the bot attack the villager p1 of player 1; the town center of player 1 stands."""
    server, me, b = armed(attack=0.0)
    healthy(server)
    server.entities["p1"]["Health"] = 25.0
    tc = combat.target_uuid([2, 2, 5, 5])
    server.forts.add(tc)
    server.hp[tc] = 2400
    b.fight()
    assert sorted(orders(server)) == [["m0", "p1"], ["m1", "p1"]]
    return server, b, tc


def look(b, seconds):
    """Looks of the bot for this many AoE2 seconds."""
    for _ in range(round(seconds / bot.LOOK)):
        b.time += bot.LOOK
        b.fight()


def test_a_soldier_that_cannot_reach_its_target_attacks_a_building():
    server, b, tc = setup()                                            # the soldiers do not move: no path
    n = len(server.log)
    look(b, bot.STALL - bot.LOOK)
    assert orders(server, n) == []                                     # not yet
    look(b, 2 * bot.LOOK)
    assert sorted(orders(server, n)) == [["m0", tc], ["m1", tc]]       # p1 in sight does not take them back
    n = len(server.log)
    look(b, 10)
    assert orders(server, n) == []


def test_a_soldier_that_does_damage_keeps_its_target():
    server, b, tc = setup()
    n = len(server.log)
    for _ in range(round(2 * bot.STALL / bot.LOOK)):
        server.entities["p1"]["Health"] -= 0.2                         # the hits of the soldiers
        look(b, bot.LOOK)
    assert orders(server, n) == [] and set(b.targets.values()) == {"p1"}


def test_a_soldier_that_comes_nearer_keeps_its_target():
    server, b, tc = setup()
    n = len(server.log)
    for _ in range(round(2 * bot.STALL / bot.LOOK)):
        for u in ("m0", "m1"):                                         # 19.5 blocks away: a long walk
            x, y, z = server.entities[u]["Pos"]
            server.entities[u]["Pos"] = (x - 1.2 * bot.LOOK / 10, y, z)
        look(b, bot.LOOK)
    assert orders(server, n) == [] and set(b.targets.values()) == {"p1"}


def test_a_given_up_unit_that_moves_is_a_target_again():
    server, b, tc = setup()
    look(b, bot.STALL + bot.LOOK)
    assert set(b.targets.values()) == {tc}
    n = len(server.log)
    server.entities["p1"]["Pos"] = (9.5, 64.0, 9.5)                   # 4 blocks away from where they gave up
    look(b, bot.LOOK)
    assert sorted(orders(server, n)) == [["m0", "p1"], ["m1", "p1"]]


def test_a_building_that_takes_no_damage_is_given_up_for_another_one():
    server, b, tc = setup()
    del server.entities["p1"]                                          # the soldiers go to the town center
    look(b, bot.LOOK)
    house = combat.target_uuid([8, 8, 10, 10])
    b.g.forts[house] = (8, 64, 8, 9, 69, 9)
    b.g.fort_players[house] = 1
    server.forts.add(house)
    server.hp[house] = 550
    n = len(server.log)
    look(b, bot.STALL + bot.LOOK)
    assert sorted(orders(server, n)) == [["m0", house], ["m1", house]]


def test_with_nothing_else_left_the_soldier_tries_the_old_target_again():
    server, b, tc = setup()
    server.forts.discard(tc)                                           # only p1 is left
    n = len(server.log)
    look(b, bot.STALL + bot.LOOK)
    assert sorted(orders(server, n)) == [["m0", "p1"], ["m1", "p1"]]


def test_a_unit_target_that_goes_on_the_water_out_of_reach_is_dropped():
    server, b, tc = setup()
    lake(b, 6, 12)                                                     # east of the town center
    server.entities["p1"]["Pos"] = (8.5, 64.0, 6.5)                    # a ship that sails away from the shore
    n = len(server.log)
    look(b, bot.LOOK)
    assert sorted(orders(server, n)) == [["m0", tc], ["m1", tc]]
