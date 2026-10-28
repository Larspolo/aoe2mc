"""The AoE2 DE lobby setting "Shared Exploration" (#2602, epic #2263; AoE2 wiki "Random map", "Team Settings"):
`game/run.py --play --shared-exploration off` takes the sight of the allies away (fog.shares)."""
import os
import sys
import types

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "game"))
import fog  # noqa: E402
import run  # noqa: E402
from test_fog_units import E1, E2, at, bare  # noqa: E402

TEAMS = {"1": {"team": 1}, "2": {"team": 1}, "3": {}}


def game(shared=None):
    """Player 1 ("v"), its ally player 2 ("a", a bot) and the enemy player 3 (E2, a bot); E1 of aoe2mc.json is near
    the ally only."""
    g = bare(TEAMS, enemies={E1: "MILITIA"})
    if shared is not None:
        g.data["shared_exploration"] = shared
    ally, foe = bare(TEAMS, player=2, villagers=("a",)), bare(TEAMS, player=3, villagers=(E2,))
    g.bots = [types.SimpleNamespace(g=ally), types.SimpleNamespace(g=foe)]
    return g, ally, foe


def update(g):
    return fog.update(g, {"v": at(10, 10), "a": at(80, 10), E1: at(81, 10), E2: at(10, 80)})


def test_by_default_the_ally_sees_for_the_player():
    for shared in (None, True):
        g, ally, foe = game(shared)
        assert update(g) == [f"aoe hide @a[team=p1] {E2}"]            # E1 is in the sight of the ally
        assert fog.shares(g, ally) and not fog.shares(g, foe)


def test_off_the_player_sees_only_through_the_own_units():
    g, ally, foe = game(False)
    assert update(g) == [f"aoe hide @a[team=p1] {E1} {E2}"]          # the ally is not hidden, E1 now is
    assert fog.shares(g, g) and not fog.shares(g, ally)
    own, enemy = fog.units(g)
    assert set(own) == {"v"} and set(enemy) == {E1, E2}               # the ally is no enemy (regen, train count them)


def test_play_writes_the_setting_for_the_fog(tmp_path, monkeypatch):
    import combat
    import gather
    from test_play_speed import FakeGame
    (tmp_path / "aoe2mc.json").write_text('{"players": [], "tile_size": 4}')
    seen = []

    class FakeGather:
        bots, villagers, units, ended, speed = (), [], [], None, 1.0

        def __init__(self, game, data, **k):
            seen.append(data["shared_exploration"])

        def setup(self):
            pass

        def run(self, seconds):
            raise StopIteration
    monkeypatch.setattr(gather, "Gather", FakeGather)
    monkeypatch.setattr(combat, "setup", lambda game, data: None)
    for value, want in (("on", True), ("off", False)):
        with pytest.raises(StopIteration):
            run.play(FakeGame(), str(tmp_path), shared_exploration=value)
        assert seen[-1] is want


def test_the_option_takes_only_on_and_off(capsys):
    with pytest.raises(SystemExit):
        run.main(["WORLD", "--play", "--shared-exploration", "x"])
    assert "invalid choice" in capsys.readouterr().err
    with pytest.raises(SystemExit):
        run.main(["--help"])
    assert "Shared Exploration" in capsys.readouterr().out
