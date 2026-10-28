"""aoe2mc.team_lines: each player 1 to 8 has its team, also a player with no units at the start (#3088). Else
"Change Ownership", "Change Player Color" and "Change Player Name" fail for that player, and its new units get no team."""
import aoe2mc


def test_a_player_without_units_gets_its_team_and_its_pulse_line():
    objects = [{"kind": "U", "player": 2, "x": 0, "y": 0}, {"kind": "B", "player": 1, "x": 0, "y": 0}]
    players = {1: {"color": "blue", "civ": "BRITONS"}, 2: {"color": "red", "civ": None}}
    load, pulse = aoe2mc.team_lines(objects, players)
    assert 'team add p1 "Player 1 (Britons)"' in load
    assert "team modify p1 color blue" in load
    assert "team join p1 @e[tag=aoe2mc.p1,team=]" in pulse


def test_gaia_and_a_player_past_8_get_no_team():
    players = {0: {"color": "light_gray"}, 9: {"color": "red"}}
    load, pulse = aoe2mc.team_lines([], players)
    assert load == [] and pulse == []


def test_a_player_of_the_scenario_without_units_has_a_team_in_the_world(tiny_world):
    import json
    import os
    path, _ = tiny_world
    with open(os.path.join(path, "datapacks", "aoe2mc", "data", "aoe2mc", "function", "load.mcfunction")) as f:
        load = f.read().splitlines()
    with open(os.path.join(path, "aoe2mc.json")) as f:
        players = json.load(f)["players"]
    for n in players:
        if 1 <= int(n) <= 8:
            assert any(line.startswith(f"team add p{n} ") for line in load)
