"""#4746: a RANDOM civilization (`run.py --civ 2=RANDOM`, or a scenario player with RANDOM) gets a civilization of civs.ROWS."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "game"))
import civs  # noqa: E402
import run  # noqa: E402

NAMES = {r["name"] for r in civs.ROWS} - {"GAIA"}


def test_random_civ_option_is_accepted():
    assert run.civ_choices(["2=random"]) == {2: "RANDOM"}


def test_random_player_gets_a_real_civilization(capsys):
    data = {"players": {"2": {"civ": "FRANKS"}}}
    run.apply_civs(data, {2: "RANDOM"})
    assert data["players"]["2"]["civ"] in NAMES
    assert "player 2: random civilization" in capsys.readouterr().err


def test_the_same_seed_gives_the_same_civilization():
    first, second = ({"players": {"2": {}}} for _ in range(2))
    run.apply_civs(first, {2: "RANDOM"}, seed=7)
    run.apply_civs(second, {2: "RANDOM"}, seed=7)
    assert first["players"]["2"]["civ"] == second["players"]["2"]["civ"]


def test_a_locked_player_keeps_its_civilization(capsys):
    data = {"players": {"2": {"civ": "SARACENS", "lock_civ": True}}}
    run.apply_civs(data, {2: "RANDOM"})
    assert data["players"]["2"]["civ"] == "SARACENS"


def test_a_scenario_player_with_random_civ_gets_a_real_one(capsys):
    data = {"players": {"1": {"civ": "RANDOM"}}}
    run.apply_civs(data, None)
    assert data["players"]["1"]["civ"] in NAMES
