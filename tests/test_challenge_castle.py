"""run.py --play --challenge destroying-a-castle: an enemy castle of player 2 and the armies, and the medal comes from
the time to destroy the castle (#3908)."""
import types

import build  # noqa: E402  (game/ is on sys.path after the import of game.challenge)
import cheats  # noqa: E402
import pytest
import recap  # noqa: E402
import train  # noqa: E402

from game import challenge

C = challenge.CHALLENGES["destroying-a-castle"]


def fake(seconds=0.0):
    g = types.SimpleNamespace(player=1, ended=None, challenge="destroying-a-castle", sent=[], forts={},
                              data={"objects": [{"kind": "building", "player": 2, "name": "TOWN_CENTER",
                                                 "footprint": [40, 40, 56, 56]}]},
                              map=types.SimpleNamespace(n=200, front=lambda rect: [(1, 1), (2, 1)], y=lambda x, z: 5))
    g.command = g.sent.append
    g.seconds = seconds
    return g


@pytest.fixture
def placed(monkeypatch):
    out = {"sites": [], "units": []}
    monkeypatch.setattr(build, "near", lambda g, name, cell, reach=12: (cell[0], cell[0] + 20, cell[1], cell[1] + 20))
    monkeypatch.setattr(build, "found", lambda g, name, rect, free=False: out["sites"].append((name, g.player, free))
                        or {"name": name, "player": g.player, "footprint": rect})
    monkeypatch.setattr(build, "rise", lambda g, site, work: None)
    monkeypatch.setattr(train, "homes", lambda g: {(100, 116, 100, 116): "TOWN_CENTER"})
    monkeypatch.setattr(train, "summon", lambda g, name, pos, player=None: out["units"].append((name, player)))
    return out


@pytest.fixture
def ends(monkeypatch):
    out = []
    monkeypatch.setattr(recap, "game_time", lambda g: g.seconds)
    monkeypatch.setattr(cheats, "over", lambda g, won: out.append(won(1)) or setattr(g, "ended", "x"))
    return out


def test_the_setup_places_a_complete_castle_of_player_2_and_both_armies(placed):
    g = fake()
    challenge.setup(g)
    assert placed["sites"] == [("CASTLE", 2, True)] and g.player == 1
    for player, key in ((2, "defenders"), (1, "army")):
        assert sorted(n for n, p in placed["units"] if p == player) == sorted(
            n for n, k in C[key].items() for _ in range(k))


def test_the_castle_falls_in_the_gold_time_the_game_ends_with_the_gold_medal(ends):
    g = fake(seconds=C["gold"] - 20)
    g.siege_target, g.forts = "castle", {"castle": (0,) * 6}
    challenge.tick(g)
    assert ends == [] and not g.ended
    g.forts.pop("castle")                                            # Gather.free: the castle fell
    challenge.tick(g)
    assert ends == [True] and any("Gold medal" in c and "subtitle" in c for c in g.sent)
