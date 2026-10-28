"""#2296: `run.py --play --teams 1,1,2,2` sets the teams of the players before the game starts."""
import json
import os
import sys
import types

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "game"))
import civs  # noqa: E402
import gather  # noqa: E402
import run  # noqa: E402

PLAYERS = {"0": {"civ": "GAIA", "team": None}, "1": {"civ": "BERBERS"}, "2": {"civ": "BRITONS"},
           "3": {"civ": "FRANKS", "team": 1}, "4": {"civ": "CELTS"}}


class FakeGame:
    kind, game_port, version, sides = "vanilla", 0, "26.3", {}

    def forceload(self):
        pass

    def command(self, c):
        pass


def players(tmp_path, monkeypatch, teams):
    """The aoe2mc.json "players" that the Gather of play() sees, with no server."""
    (tmp_path / "aoe2mc.json").write_text(json.dumps({"players": PLAYERS, "tile_size": 4}))
    seen = []

    class FakeGather:
        bots, villagers, units, ended, speed = (), [], [], None, 1.0

        def __init__(self, game, data, player, **k):
            self.data = data

        def setup(self):
            seen.append(self.data["players"])

        def run(self, seconds):
            pass
    monkeypatch.setattr(gather, "Gather", FakeGather)
    import combat
    monkeypatch.setattr(combat, "setup", lambda game, data: None)
    run.play(FakeGame(), str(tmp_path), teams=teams)
    return seen[0]


def test_teams_option_makes_the_allies(tmp_path, monkeypatch):
    p = players(tmp_path, monkeypatch, run.team_choices("1,1,2,2", PLAYERS))
    assert gather.allied(p, 1, 2) and gather.allied(p, 3, 4)
    assert not gather.allied(p, 1, 3) and not gather.allied(p, 2, 4)
    assert gather.allies_command(p) == "aoe allies p1,p2 p3,p4"
    berber_ally = types.SimpleNamespace(data={"players": p}, player=2)
    assert not civs.missing(berber_ally, "GENITOUR")                 # the shared unit of the Berber ally
    assert civs.missing(types.SimpleNamespace(data={"players": p}, player=4), "GENITOUR")


def test_no_team_and_no_option(tmp_path, monkeypatch):
    p = players(tmp_path, monkeypatch, run.team_choices("-,-,-,-", PLAYERS))
    assert not any(gather.allied(p, 3, b) for b in (1, 2, 4))        # "-" removes the scenario team of player 3
    assert players(tmp_path, monkeypatch, None)["3"]["team"] == 1    # no option: the teams of the scenario


@pytest.mark.parametrize("value", ["1,1,2", "1,1,2,2,3", "1,1,5,2", "1,a,2,2", ""])
def test_wrong_teams_stop_with_a_message(value):
    with pytest.raises(SystemExit) as e:
        run.team_choices(value, PLAYERS)
    assert "4 teams" in str(e.value) and "1 to 4 or -" in str(e.value)
