"""Every sample record names its players by the name of the record, else "Player N" (#5025, #4666)."""
import glob
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import replay  # noqa: E402
from test_replay import data  # noqa: E402
from test_replay_control import Clock  # noqa: E402

from aoe2mc import read_record  # noqa: E402

pytestmark = pytest.mark.slow  # each sample is parsed (about 10 s)
SAMPLES = sorted(glob.glob("samples/*.aoe2record"))


def label(players, n):
    """The name text of player n, with its number as key (test_replay_names.named keys every player as 1)."""
    d = data([])
    d["players"] = {str(n): players[n]}
    return replay.Replay(Clock(), d).player(n)[0]


@pytest.mark.parametrize("path", SAMPLES)
def test_each_player_is_named_by_the_record_or_by_its_number(path):
    players = read_record(path)[6]
    assert [n for n in players if n > 0], "a sample has at least one player"
    for n in players:
        if n == 0:
            continue
        name = players[n].get("name")
        if name:
            expected = name if len(name) <= 16 else name[:15] + "…"
        else:
            expected = f"Player {n}"
        assert label(players, n).startswith(expected), (path, n)


def test_the_samples_with_names_give_names():
    names = [p.get("name") for path in SAMPLES for n, p in read_record(path)[6].items() if n > 0]
    assert any(names)
