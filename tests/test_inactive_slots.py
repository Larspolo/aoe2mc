"""#5033: the inactive player slots of a scenario get no Diplomacy column and no random civilization."""
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "game"))
import diplomacy  # noqa: E402
import run  # noqa: E402
from test_scenario_mode import game  # noqa: E402

ROOT = os.path.join(os.path.dirname(__file__), "..")


def test_four_active_players_give_three_columns(tmp_path):
    scn, out = tmp_path / "f.aoe2scenario", tmp_path / "W"
    subprocess.run([sys.executable, "tools/scenarios.py", "four_civs", str(scn)], cwd=ROOT, check=True)
    subprocess.run([sys.executable, "aoe2mc.py", str(scn), str(out), "--no-units"], cwd=ROOT, check=True,
                   capture_output=True)
    players = json.load(open(out / "aoe2mc.json"))["players"]
    _, g, _ = game(players)
    g.player = 1
    assert diplomacy.others(g) == [2, 3, 4]


def test_an_inactive_slot_gets_no_random_civilization(capsys):
    data = {"players": {"1": {"civ": "RANDOM"}, "5": {"civ": "RANDOM", "active": False}}}
    run.apply_civs(data, {})
    assert data["players"]["5"]["civ"] == "RANDOM" and "player 5" not in capsys.readouterr().err
