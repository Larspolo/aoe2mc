"""run.py --play --challenge fast-castle-age: the goal function "challenge.castle" ends the game with its medal (#3902)."""
import types

import pytest

from game import challenge

import build  # noqa: E402  (game/ is on sys.path after the import of game.challenge)
import recap  # noqa: E402
import cheats  # noqa: E402

C = challenge.CHALLENGES["fast-castle-age"]
N = C["need"]


def fake(villagers=N["villagers"], houses=N["houses"], seconds=0.0):
    """A Gather of player 1 with the full goal of Fast Castle Age."""
    g = types.SimpleNamespace(player=1, ended=None, challenge="fast-castle-age", sent=[], data={"objects": []},
                              villagers={f"v{i}": None for i in range(villagers)},
                              techs={build.AGE_TECHS[0], build.AGE_TECHS[1]},
                              sites=[{"name": "HOUSE", "done": True, "player": 1} for _ in range(houses)])
    g.command = g.sent.append
    g.seconds = seconds
    return g


@pytest.fixture
def ends(monkeypatch):
    out = []
    monkeypatch.setattr(recap, "game_time", lambda g: g.seconds)
    monkeypatch.setattr(cheats, "over", lambda g, won: out.append(won(1)) or setattr(g, "ended", "x"))
    return out


def test_the_full_goal_in_the_gold_time_ends_the_game_with_the_gold_medal(ends):
    g = fake(seconds=C["gold"])
    challenge.tick(g)
    assert ends == [True] and any("Gold medal" in c and "subtitle" in c for c in g.sent)


@pytest.mark.parametrize("less", ["houses", "villagers"])
def test_a_goal_with_fewer_houses_or_villagers_does_not_end_the_game(ends, less):
    g = fake(seconds=C["gold"], **{less: N[less] - 1})
    challenge.tick(g)
    assert ends == [] and not g.ended


def test_the_castle_age_is_needed(ends):
    g = fake(seconds=C["gold"])
    g.techs = {build.AGE_TECHS[0]}
    challenge.tick(g)
    assert ends == [] and not g.ended
