"""The foe of a bot is never its ally (#3107): scenario.bot_seats, run.bot_seat, run.play and Bot.fight."""
import types

from test_bot_attack import armed, orders

from game import run, scenario

TWO_V_TWO = {"0": {}, "1": {"team": 1}, "2": {"computer": True, "team": 1},
             "3": {"computer": True, "team": 2}, "4": {"computer": True, "team": 2}}


def test_a_bot_of_a_2v2_scenario_attacks_the_other_team():
    seats = scenario.bot_seats(TWO_V_TWO, 1)
    assert seats == [(2, 3), (3, 1), (4, 1)]
    assert not any(TWO_V_TWO[str(b)]["team"] == TWO_V_TWO[str(f)]["team"] for b, f in seats)


def test_a_bot_with_only_allies_has_no_foe():
    players = {"1": {"team": 1}, "2": {"computer": True, "team": 1}, "3": {"computer": True, "team": 1}}
    assert scenario.bot_seats(players, 1) == [(2, None), (3, None)]


def test_a_bot_in_the_team_of_all_people_has_no_foe():
    assert run.bot_seat({"1": {"team": 1}, "2": {"team": 1}, "3": {"team": 1}}, 2) == (3, None)
    assert run.bot_seat({"1": {"team": 1}, "2": {"team": 1}, "3": {"team": 1}, "4": {}}, 2) == (3, 4)


def test_a_bot_with_no_foe_never_attacks():
    server, me, b = armed(attack=0.0)
    b.foe = None
    b.fight()
    assert orders(server) == []


def test_the_wave_goes_to_the_units_that_the_foe_trained():
    server, me, b = armed(attack=0.0)
    b.foe = 3
    three = types.SimpleNamespace(player=3, villagers={"v3": "VILLAGER"}, soldiers={})
    me.bots = [b, types.SimpleNamespace(g=three)]
    me.soldiers["s1"] = "MILITIA"                                      # trained by player 1: no target
    server.entities["v3"] = {"Pos": (20.5, 64.0, 26.5)}
    server.entities["s1"] = {"Pos": (20.5, 64.0, 25.5)}
    b.fight()
    assert sorted(orders(server)) == [["m0", "v3"], ["m1", "v3"]]
