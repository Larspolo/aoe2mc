"""run.py --play --challenge booming: 100 villagers and the Imperial Age complete the goal (#3903, epic #3759)."""
import types

import pytest

from game import challenge

import build  # noqa: E402  (game/ is on sys.path after the import of game.challenge)
import cheats  # noqa: E402
import recap  # noqa: E402


def fake(villagers=100, seconds=590.0):
    """A Gather of player 1 with the goal of Booming: the villagers and the three ages, nothing else."""
    g = types.SimpleNamespace(player=1, ended=None, challenge="booming", sent=[], data={"objects": []},
                              stock={}, villagers={f"v{i}": None for i in range(villagers)},
                              techs=set(build.AGE_TECHS), sites=[], seconds=seconds)
    g.command = g.sent.append
    return g


@pytest.fixture
def ends(monkeypatch):
    out = []
    monkeypatch.setattr(recap, "game_time", lambda g: g.seconds)
    monkeypatch.setattr(cheats, "over", lambda g, won: out.append(won(1)) or setattr(g, "ended", "x"))
    return out


def test_100_villagers_and_the_imperial_age_end_the_game_with_the_gold_medal(ends):
    g = fake()
    challenge.tick(g)
    assert ends == [True] and any("Gold medal" in c and "subtitle" in c for c in g.sent)


def test_99_villagers_do_not_complete_the_goal(ends):
    g = fake(villagers=99)
    challenge.tick(g)
    assert ends == [] and g.ended is None
