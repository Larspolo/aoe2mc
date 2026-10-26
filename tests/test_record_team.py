"""The recorded team game in samples/ (#1190): 2 vs 2, read with its license note, its teams and its timeline."""
import os

import pytest

import aoe2mc

REC = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "samples", "de-63.0.aoe2record")


def test_team_record_has_license_note():
    assert os.path.getsize(REC) < 5_000_000
    assert "MIT License" in open(REC + ".LICENSE.txt").read()


def test_team_record_has_two_teams_and_commands_of_each_player():
    model = pytest.importorskip("mgz.model")
    with open(REC, "rb") as f:
        match = model.parse_match(f)
    assert match.map.name == "Arena"
    assert [p.civilization for p in match.players] == ["Maya", "Aztecs", "Spanish", "Goths"]
    assert [p.team_id for p in match.players] == [[1, 3], [2, 4], [1, 3], [2, 4]]
    timeline = aoe2mc.read_timeline(REC)
    assert {e["player"] for e in timeline if e["kind"] == "build"} == {1, 2, 3, 4}
