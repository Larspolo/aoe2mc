"""--civ N=RANDOM: one civilization of all civilizations, the same for the same scenario (#4755)."""
from game import civs, run


def _data():
    return {"map_size": 120, "objects": [{}] * 7, "players": {"1": {"civ": "FRANKS"}, "2": {}}}


def test_random_gives_a_known_civilization_deterministically():
    choices = run.civ_choices(["2=random"])
    assert choices == {2: "RANDOM"}
    a, b = _data(), _data()
    run.apply_civs(a, choices)
    run.apply_civs(b, choices)
    assert a["players"]["2"]["civ"] in {r["name"] for r in civs.ROWS}
    assert a["players"]["2"]["civ"] == b["players"]["2"]["civ"]
    assert a["players"]["1"]["civ"] == "FRANKS"


def test_random_keeps_a_locked_civilization():
    data = _data()
    data["players"]["2"] = {"civ": "FRANKS", "lock_civ": True}
    run.apply_civs(data, {2: "RANDOM"})
    assert data["players"]["2"]["civ"] == "FRANKS"


def test_a_scenario_player_with_random_civ_gets_a_real_one(capsys):
    data = {"players": {"1": {"civ": "RANDOM"}}}
    run.apply_civs(data, None)
    assert data["players"]["1"]["civ"] in {r["name"] for r in civs.ROWS} - {"GAIA"}
    assert "player 1: the scenario civilization RANDOM gives" in capsys.readouterr().err
