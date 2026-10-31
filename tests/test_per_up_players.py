"""Find a player and read the allies in AI scripts: up-find-player, up-find-next-player, up-players-in-game,
up-player-distance, up-allied-goal, up-allied-sn (#4872). The map of test_bot_gather (tile size 1): the bot is player 2,
the person player 1 is an enemy; stubs add player 3 (an ally with a script) and player 4 (an enemy)."""
import types

from test_bot_gather import bot_map

from game import per


def script():
    server, me, b = bot_map()
    ally = types.SimpleNamespace(g=types.SimpleNamespace(player=3, sites=[]))
    ally.script = per.Script([], ally)
    foe = types.SimpleNamespace(g=types.SimpleNamespace(player=4, sites=[]), script=None)
    me.bots = [b, ally, foe]                                           # run.py: player 1 holds the bots
    for g in (me, b.g):
        g.players.update({"2": {**g.players.get("2", {}), "team": 1}, "3": {"team": 1}, "4": {}})
    b.g.data["objects"] += [{"kind": "building", "name": "HOUSE", "player": 4, "footprint": [26, 26, 27, 27]},
                            {"kind": "building", "name": "HOUSE", "player": 3, "footprint": [10, 10, 11, 11]}]
    return per.Script([], b), b, ally


def found(s, *args, goal=9):
    s.act(None, (args[0], args[1], args[2], goal))
    return s.goals[goal]


def test_the_four_methods_of_up_find_player_and_the_cycle_of_up_find_next_player():
    s, b, ally = script()
    assert found(s, "up-find-player", "enemy", "find-attacker") == 0  # the game program keeps no attacker
    assert found(s, "up-find-player", "enemy", "find-closest") == 4   # 8 tiles away; player 1 is 25 tiles away
    assert found(s, "up-find-player", "enemy", "find-ordered") == 4
    assert found(s, "up-find-player", "enemy", "find-random") in (1, 4)
    assert found(s, "up-find-player", "ally", "find-ordered") == 3
    assert found(s, "up-find-player", "neutral", "find-ordered") == 0  # no player: 0
    s.goals[9] = 4
    assert [found(s, "up-find-next-player", "enemy", "find-ordered") for _ in range(3)] == [1, 4, 1]


def test_players_in_game_distance_and_the_allied_goal_and_number():
    s, b, ally = script()
    assert s.check(("up-players-in-game", "enemy", "==", 2)) and s.check(("up-players-in-game", "any", "==", 3))
    assert s.check(("up-player-distance", 4, "==", 8)) and s.check(("up-player-distance", 1, ">", 20))
    ally.script.goals[5] = 8
    sn = next(iter(per.SN))
    ally.script.sn[sn] = 123
    assert s.check(("up-allied-goal", 3, 5, "==", 8)) and not s.check(("up-allied-goal", 3, 5, "==", 7))
    assert s.check(("up-allied-sn", 3, sn, "==", 123))
    assert not s.check(("up-allied-goal", 4, 5, "==", -1))              # an enemy: false
