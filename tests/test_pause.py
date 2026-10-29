"""#3374: pause.toggle freezes the ticks of the server, and Gather.run skips its steps while the game is paused."""
import os
import sys
import types

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "game"))
import gather  # noqa: E402
import pause  # noqa: E402
import recap  # noqa: E402


def fake(now):
    g = object.__new__(gather.Gather)
    g.tick, g.speed, g.bots, g.ended, g.t0 = 0.25, 1.0, (), None, 0.0
    g.clock = lambda: now[0]
    g.game = types.SimpleNamespace()
    g.commands = []
    g.command = g.commands.append
    return g


def test_toggle_freezes_and_unfreezes():
    g = fake([10.0])
    assert pause.toggle(g, 2) is True
    assert pause.toggle(g, 2) is False
    assert [c for c in g.commands if c.startswith("tick")] == ["tick freeze", "tick unfreeze"]
    assert "Player 2 paused the game." in g.commands[1] and "Player 2 continued the game." in g.commands[3]


def test_a_paused_gather_does_not_step_and_keeps_its_game_time(monkeypatch):
    now = [10.0]
    g = fake(now)
    steps, clicks = [], []
    g.point = lambda: None
    g.step = lambda: steps.append(1)
    g.clicks = lambda: clicks.append(1) or ()
    monkeypatch.setattr(gather.time, "sleep", lambda s: None)
    pause.toggle(g, 1)
    before = recap.game_time(g)
    g.run(until=lambda: len(clicks) >= 4)
    assert steps == [] and len(clicks) >= 4                            # the clicks still run: a menu can continue
    now[0] += 5.0
    pause.toggle(g, 1)
    assert recap.game_time(g) == pytest.approx(before)
