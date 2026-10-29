"""run.py --play --challenge: an Art of War challenge ends with its medal (#3900)."""
import types

import pytest

from game import challenge, run

import build  # noqa: E402  (game/ is on sys.path after the import of game.challenge)
import cheats  # noqa: E402
import recap  # noqa: E402


def fake(villagers=21, seconds=0.0):
    """A Gather of player 1 with the full goal of Early Economy, but villagers."""
    g = types.SimpleNamespace(player=1, ended=None, challenge="early-economy", sent=[], data={"objects": []},
                              stock={"food": 200, "wood": 210, "gold": 100, "stone": 200},
                              villagers={f"v{i}": None for i in range(villagers)}, techs={build.AGE_TECHS[0]},
                              sites=[{"name": n, "done": True, "player": 1} for n in ("LUMBER_CAMP", "MILL")])
    g.command = g.sent.append
    g.seconds = seconds
    return g


@pytest.fixture
def ends(monkeypatch):
    out = []
    monkeypatch.setattr(recap, "game_time", lambda g: g.seconds)
    monkeypatch.setattr(cheats, "over", lambda g, won: out.append(won(1)) or setattr(g, "ended", "x"))
    return out


@pytest.mark.parametrize("seconds, text, won", [(470, "Gold medal", True), (650, "Bronze medal", True),
                                                (781, "No medal", False)])
def test_a_complete_goal_ends_the_game_with_the_medal_of_the_time(ends, seconds, text, won):
    g = fake(seconds=seconds)
    challenge.tick(g)
    assert ends == [won] and any(text in c and "subtitle" in c for c in g.sent)


def test_after_the_bronze_limit_the_game_ends_with_no_medal(ends):
    g = fake(villagers=5, seconds=781)
    challenge.tick(g)
    assert ends == [False] and g.medal is None and any("No medal" in c for c in g.sent)


def test_an_incomplete_goal_does_not_end_the_game_and_shows_the_next_limit(ends):
    g = fake(villagers=20, seconds=108)
    challenge.tick(g)
    assert ends == [] and not g.ended
    assert any("bossbar set aoe2mc:challenge name" in c and "Gold medal in 6:12" in c for c in g.sent)


def test_the_challenge_gives_player_1_its_civilization():
    assert challenge.CHALLENGES["early-economy"]["civ"] == "BYZANTINES" and run.SETTINGS["challenge"] is None


def test_an_unknown_challenge_lists_the_9_names(capsys):
    with pytest.raises(SystemExit):
        run.main(["WORLD", "--play", "--challenge", "nope"])
    err = capsys.readouterr().err
    assert all(n in err for n in challenge.CHALLENGES) and len(challenge.CHALLENGES) == 9
