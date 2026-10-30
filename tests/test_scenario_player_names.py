"""#3295 (epic #2538): the player names of a scenario ("Players" tab of the editor) and the locked civilizations
("Lock Civilizations"): a locked player keeps its scenario civilization when the game program sets another one."""
import json

import scenarios

import aoe2mc
from game import diplomacy, run


def named(path, name="Saladin", lock=False):
    scn = scenarios.new_scenario(24)
    two = scn.player_manager.players[2]
    two.tribe_name, two.lock_civ = name, int(lock)
    return scenarios.save(scn, path)


def test_aoe2mc_json_has_the_name_of_the_scenario_player(tmp_path):
    aoe2mc.main([named(str(tmp_path / "s.aoe2scenario")), str(tmp_path / "W")])
    with open(tmp_path / "W" / "aoe2mc.json") as f:
        players = json.load(f)["players"]
    assert players["2"]["name"] == "Saladin" and "name" not in players["1"]


def test_an_empty_or_default_name_keeps_the_default(tmp_path):
    for name in ("", "Player 2"):
        aoe2mc.main([named(str(tmp_path / "s.aoe2scenario"), name), str(tmp_path / "W")])
        with open(tmp_path / "W" / "aoe2mc.json") as f:
            assert "name" not in json.load(f)["players"]["2"]


def test_the_start_sets_the_display_name_of_the_team():
    load, _ = aoe2mc.team_lines([], {2: {"civ": "SARACENS", "color": "red", "name": "Saladin"}})
    assert 'team modify p2 displayName {"text": "Saladin"}' in load


def test_diplomacy_shows_the_name_and_the_civilization():
    g = type("G", (), {"players": {"2": {"civ": "SARACENS", "name": "Saladin"}}})()
    assert diplomacy.name(g, 2) == "Saladin (Saracens)"
    g.players["2"].pop("name")
    assert diplomacy.name(g, 2) == "Player 2 (Saracens)"


def test_a_locked_civilization_keeps_the_scenario_civ(capsys):
    data = {"players": {"2": {"civ": "SARACENS", "lock_civ": True}, "1": {"civ": "FRANKS"}}}
    run.apply_civs(data, {"2": "BRITONS", "1": "BRITONS"})
    assert data["players"]["2"]["civ"] == "SARACENS" and data["players"]["1"]["civ"] == "BRITONS"
    assert "scenario locks" in capsys.readouterr().err
