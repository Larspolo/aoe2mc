"""The Regicide record of the owner (samples/de-regicide, #4900): the replay plays it to its end, and player 1, who
deletes the own King at 10:02.9, is out. Fake clock and RCON."""
import contextlib
import io
import json
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import replay  # noqa: E402
from test_replay_control import Clock  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REC = os.path.join(ROOT, "samples", "de-regicide.aoe2record")


@pytest.mark.slow
def test_the_regicide_sample_replays_to_its_end_and_the_deleted_king_puts_player_1_out(tmp_path):
    import aoe2mc
    with contextlib.redirect_stdout(io.StringIO()):
        aoe2mc.convert(REC, str(tmp_path / "W"))
    with open(tmp_path / "W" / "aoe2mc.json") as f:
        d = json.load(f)
    assert d["lobby"]["type"] == replay.REGICIDE                       # by the start Kings (#4970)
    game = Clock()
    r = replay.Replay(game, d)
    assert set(r.kings) == {1, 2}
    r.run(clock=lambda: game.now, sleep=game.sleep, log=None)
    assert list(r.regicided) == [1] and 600000 <= r.regicided[1] <= 604000
