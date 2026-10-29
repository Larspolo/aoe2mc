"""run.py --play --challenge defending-against-a-rush: enemy waves attack the town center, the Castle Age with a town
center completes the goal, a lost town center is a defeat (#3907, epic #3759)."""
import types

import pytest

from game import challenge

import build  # noqa: E402  (game/ is on sys.path after the import of game.challenge)
import cheats  # noqa: E402
import combat  # noqa: E402
import recap  # noqa: E402
import train  # noqa: E402

TC = (40, 56, 40, 56)


def fake(seconds=100.0, ages=1, town=True):
    """A Gather of player 1 in Defending Against A Rush on a 128-block map."""
    g = types.SimpleNamespace(player=1, ended=None, challenge="defending-against-a-rush", sent=[], data={"objects": []},
                              seconds=seconds, ages=ages, town=town,
                              map=types.SimpleNamespace(n=128, T=4, y=lambda x, z: 5))
    g.command = g.sent.append
    return g


@pytest.fixture
def game(monkeypatch):
    out = []
    monkeypatch.setattr(recap, "game_time", lambda g: g.seconds)
    monkeypatch.setattr(cheats, "over", lambda g, won: out.append(won(1)) or setattr(g, "ended", "x"))
    monkeypatch.setattr(build, "ages", lambda g: g.ages)
    monkeypatch.setattr(train, "homes", lambda g: {TC: "TOWN_CENTER"} if g.town else {})
    monkeypatch.setattr(train, "summon", lambda g, name, pos, player=None: g.sent.append((name, pos, player)) or name.lower())
    return out


def test_the_first_wave_comes_at_its_time_and_attacks_the_town_center(game):
    first = challenge.CHALLENGES["defending-against-a-rush"]["attacks"][0]
    g = fake(seconds=first["at"] - 1)
    challenge.tick(g)
    assert not [c for c in g.sent if isinstance(c, tuple)]
    g.seconds = first["at"]
    challenge.tick(g)
    summoned = [c for c in g.sent if isinstance(c, tuple)]
    assert sorted(n for n, _, _ in summoned) == sorted(n for n, k in first["units"].items() for _ in range(k))
    assert all(p == 2 and pos[0] > 100 and pos[2] > 100 for _, pos, p in summoned)   # the far corner of the map
    target = combat.target_uuid([TC[0], TC[2], TC[1], TC[3]])
    assert [c for c in g.sent if isinstance(c, str) and c.startswith("aoe attack")] == \
        [f"aoe attack {n.lower()} {target}" for n, _, _ in summoned]
    challenge.tick(g)                                                  # a wave comes once
    assert len([c for c in g.sent if isinstance(c, tuple)]) == len(summoned) and g.challenge_attacks == 1


def test_the_castle_age_at_470_seconds_with_a_town_center_gives_the_gold_medal(game):
    g = fake(seconds=470.0, ages=2)
    challenge.tick(g)
    assert game == [True] and any("Gold medal" in c and "subtitle" in c for c in g.sent if isinstance(c, str))


def test_a_lost_town_center_ends_the_game_with_defeat(game):
    g = fake(seconds=300.0, town=False)
    challenge.tick(g)
    assert game == [False] and g.medal is None and any("No medal" in c for c in g.sent if isinstance(c, str))
