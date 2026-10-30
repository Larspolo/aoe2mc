"""The allies of a scenario (#1793): players with the mutual stance ally (DiplomacyState.ALLY) get one team in
aoe2mc.json (`players[N]["team"]`), so that the game program treats them as allies (gather.allied, #1312)."""
import json

import scenarios
from AoE2ScenarioParser.datasets.players import PlayerId
from AoE2ScenarioParser.datasets.trigger_lists import DiplomacyState

import aoe2mc
from game import gather


def scenario(path, allies=(), players=4):
    """allies: (a, b) pairs, a has the stance ally to b (one way)."""
    scn = scenarios.new_scenario(24)
    scn.player_manager.active_players = players
    for a, b in allies:
        scn.player_manager.players[a].set_player_diplomacy(PlayerId(b), DiplomacyState.ALLY)
    return scenarios.save(scn, str(path))


def teams(tmp_path, allies, players=4):
    p = aoe2mc.read_scenario(scenario(tmp_path / "t.aoe2scenario", allies, players))[-1]
    return {int(n): q.get("team") for n, q in p.items() if "team" in q}



def test_two_mutual_allies_are_team_1_and_the_enemy_has_no_team(tmp_path):
    assert teams(tmp_path, [(1, 2), (2, 1)], 3) == {1: 1, 2: 1}


def test_a_one_way_ally_makes_no_team(tmp_path):
    assert teams(tmp_path, [(1, 2)], 3) == {}


def test_two_teams_are_numbered_from_the_lowest_player(tmp_path):
    assert teams(tmp_path, [(2, 4), (4, 2), (1, 3), (3, 1)]) == {1: 1, 3: 1, 2: 2, 4: 2}


def test_allies_of_allies_are_one_team(tmp_path):
    assert teams(tmp_path, [(1, 2), (2, 1), (2, 3), (3, 2)]) == {1: 1, 2: 1, 3: 1}


def test_a_scenario_with_no_ally_has_no_team_key(tmp_path):
    assert teams(tmp_path, []) == {}


def test_aoe2mc_json_keeps_the_teams_for_the_plugin(tmp_path):
    src = scenario(tmp_path / "t.aoe2scenario", [(1, 2), (2, 1)], 3)
    aoe2mc.main([src, str(tmp_path / "W")])
    with open(tmp_path / "W" / "aoe2mc.json") as f:
        players = json.load(f)["players"]
    assert players["1"]["team"] == players["2"]["team"] == 1 and "team" not in players["3"]
    assert gather.allies_command(players) == "aoe allies p1,p2"
    assert gather.allied(players, 1, 2) and not gather.allied(players, 1, 3)
