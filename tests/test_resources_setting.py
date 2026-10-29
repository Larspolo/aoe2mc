"""The AoE2 DE setting "Starting resources" of the game program (#2264, epic #2263): `game/run.py --resources LEVEL`
gives each player the start resources of the level (AoE2 wiki, "Random map"), with the civilization bonus on top."""
import pytest
from test_gather import FakeServer, grid

from game import gather, run


def stock(civ=None, **kw):
    data = grid([[64] * 8 for _ in range(8)], [])
    if civ:
        data["players"] = {"1": {"civ": civ}}
    return gather.Gather(FakeServer({}), data, **kw).stock


def test_each_level_gives_its_resources():
    for level, want in gather.LEVELS.items():
        assert dict(stock(resources=level)) == want, level


def test_the_civilization_bonus_comes_on_top():
    base, civ = stock(resources="high"), stock("CHINESE", resources="high")
    assert civ != base                                                  # the same bonus at each level
    assert {k: civ[k] - base[k] for k in base} == {k: stock("CHINESE")[k] - stock()[k] for k in base}


def test_standard_is_the_start_of_today():
    assert stock() == stock(resources="standard") == gather.START


def test_run_offers_each_level(capsys):
    with pytest.raises(SystemExit):
        run.main(["--help"])
    help_text = capsys.readouterr().out
    assert "--resources {" + ",".join([*gather.LEVELS, *gather.RANDOM]) + "}" in help_text
