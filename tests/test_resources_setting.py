"""The AoE2 DE setting "Starting resources" of the game program (#2264, epic #2263): `game/run.py --resources LEVEL`
gives each player the start resources of the level (AoE2 wiki, "Random map"), with the civilization bonus on top."""
import pytest
from test_gather import FakeServer, grid

from game import gather, run

WIKI = {"standard": (200, 200, 100, 200), "low": (200, 200, 100, 200), "medium": (500, 500, 300, 400),
        "high": (1000, 1000, 700, 800), "ultra": (20000, 20000, 10000, 5000)}      # food, wood, gold, stone


def stock(civ=None, **kw):
    data = grid([[64] * 8 for _ in range(8)], [])
    if civ:
        data["players"] = {"1": {"civ": civ}}
    return gather.Gather(FakeServer({}), data, **kw).stock


def test_each_level_gives_the_wiki_resources():
    for level, (food, wood, gold, stone) in WIKI.items():
        assert stock(resources=level) == {"food": food, "wood": wood, "gold": gold, "stone": stone}, level


def test_the_civilization_bonus_comes_on_top():
    assert stock("CHINESE", resources="high") == {"food": 800, "wood": 950, "gold": 700, "stone": 800}


def test_standard_is_the_start_of_today():
    assert stock() == stock(resources="standard") == gather.START


def test_run_offers_each_level(capsys):
    with pytest.raises(SystemExit):
        run.main(["--help"])
    help_text = capsys.readouterr().out
    assert "--resources {" + ",".join(gather.LEVELS) + "}" in help_text
