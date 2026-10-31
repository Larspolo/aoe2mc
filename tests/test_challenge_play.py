"""run.py --play --challenge: an Art of War challenge ends with its medal (#3900)."""
import types

import build  # noqa: E402  (game/ is on sys.path after the import of game.challenge)
import cheats  # noqa: E402
import pytest
import recap  # noqa: E402

from game import challenge, run

C = challenge.CHALLENGES["early-economy"]
N = C["need"]


def fake(villagers=N["villagers"], seconds=0.0):
    """A Gather of player 1 with the full goal of Early Economy, but villagers."""
    g = types.SimpleNamespace(player=1, ended=None, challenge="early-economy", sent=[], data={"objects": []},
                              stock={r: N.get(r, 0) + 10 for r in ("food", "wood", "gold", "stone")},
                              villagers={f"v{i}": None for i in range(villagers)}, techs={build.AGE_TECHS[0]},
                              sites=[{"name": n, "done": True, "player": 1} for n in N.get("buildings", ())])
    g.command = g.sent.append
    g.seconds = seconds
    return g


@pytest.fixture
def ends(monkeypatch):
    out = []
    monkeypatch.setattr(recap, "game_time", lambda g: g.seconds)
    monkeypatch.setattr(cheats, "over", lambda g, won: out.append(won(1)) or setattr(g, "ended", "x"))
    return out


@pytest.mark.parametrize("seconds, text, won", [(C["gold"] - 10, "Gold medal", True), (C["silver"] + 1, "Bronze medal", True),
                                                (C["bronze"] + 1, "No medal", False)])
def test_a_complete_goal_ends_the_game_with_the_medal_of_the_time(ends, seconds, text, won):
    g = fake(seconds=seconds)
    challenge.tick(g)
    assert ends == [won] and any(text in c and "subtitle" in c for c in g.sent)


def test_after_the_bronze_limit_the_game_ends_with_no_medal(ends):
    g = fake(villagers=5, seconds=C["bronze"] + 1)
    challenge.tick(g)
    assert ends == [False] and g.medal is None and any("No medal" in c for c in g.sent)


def test_an_incomplete_goal_does_not_end_the_game_and_shows_the_next_limit(ends):
    g = fake(villagers=N["villagers"] - 1, seconds=108)
    challenge.tick(g)
    assert ends == [] and not g.ended
    left = C["gold"] - 108
    assert any("bossbar set aoe2mc:challenge name" in c and f"Gold medal in {left // 60}:{left % 60:02d}" in c
               for c in g.sent)


def test_an_unknown_challenge_lists_the_names(capsys):
    with pytest.raises(SystemExit):
        run.main(["WORLD", "--play", "--challenge", "nope"])
    err = capsys.readouterr().err
    assert all(n in err for n in challenge.CHALLENGES)
