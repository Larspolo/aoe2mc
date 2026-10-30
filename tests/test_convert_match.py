"""aoe2mc.py --match GAME:PROFILE downloads the record of a match once and converts it (#4484)."""
import json
import os
import shutil

import pytest

import aoe2mc
from tools import record_api

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REC = os.path.join(ROOT, "samples", "de-64.3.aoe2record")
pytest.importorskip("mgz.model")


def objects(world):
    return json.load(open(os.path.join(world, "aoe2mc.json")))["objects"]


def test_match_converts_the_record_once(tmp_path, monkeypatch):
    calls = []

    def download(game, profile, folder):
        calls.append((game, profile))
        return shutil.copy(REC, os.path.join(folder, "AgeIIDE_Replay_1.aoe2record"))

    monkeypatch.setattr(record_api, "download", download)
    monkeypatch.chdir(tmp_path)
    aoe2mc.main(["--match", "1:2", "a", "--no-units"])
    aoe2mc.main([REC, "b", "--no-units"])
    assert calls == [("1", "2")]
    assert objects("a") == objects("b")
    aoe2mc.main(["--match", "1:2", "c", "--no-units"])
    assert calls == [("1", "2")]


@pytest.mark.parametrize("argv", [["--match", "1:2", REC, "out"], ["--match", "x", "out"]])
def test_match_errors(argv, capsys):
    with pytest.raises(SystemExit):
        aoe2mc.main(argv)
    assert "--match" in capsys.readouterr().err
