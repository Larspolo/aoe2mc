"""tools/replay_shot.py --camera --info (#5461): the info line check of a live replay counts the action bar lines of
Replay.inspect, without a client."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
import replay_shot  # noqa: E402

UNIT = 'title aoe2mc actionbar [{"translate": "aoe2mc.replay.inspect", "with": []}]'
HOUSE = 'title aoe2mc actionbar [{"translate": "aoe2mc.replay.building_hp", "with": []}]'


def test_the_summary_counts_the_units_and_buildings_and_keeps_the_first_line_of_each():
    out = replay_shot.summary([(11000, HOUSE), (12500.7, UNIT), (65000, UNIT)])
    assert out == {"unit": 2, "building": 1, "first": {"building": ["0:11", HOUSE], "unit": ["0:12", UNIT]}}
    assert replay_shot.summary([]) == {"unit": 0, "building": 0, "first": {}}


def run(monkeypatch, tmp_path, lines):
    seen = {}

    def fake(*a, camera=None, info=None):
        seen.update(camera=camera)
        info.extend(lines)
        return []
    monkeypatch.setattr(replay_shot, "run_shots", fake)
    path = tmp_path / "c.json"
    rc = replay_shot.main(["rec.aoe2record", "o.png", "--at-time", "1:00", "--camera", "player", "--info", str(path)])
    return rc, seen, json.loads(path.read_text())


def test_the_check_passes_with_a_unit_line_and_passes_the_camera(monkeypatch, tmp_path):
    rc, seen, out = run(monkeypatch, tmp_path, [(11000, UNIT)])
    assert rc == 0 and seen["camera"] == "player" and out["unit"] == 1


def test_the_check_fails_with_no_unit_line(monkeypatch, tmp_path):
    rc, _, out = run(monkeypatch, tmp_path, [(11000, HOUSE)])
    assert rc == 1 and out["unit"] == 0 and out["building"] == 1
