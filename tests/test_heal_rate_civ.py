"""The civilization key "heal_rate" (Antiquity Mode Romans, the team bonus: priests heal 50 % faster, #4789) multiplies the
heal rate of monk.heal, for the player of the civilization and its allies. Test data only: a monkeypatched line of the key."""
import civs
import pytest
from test_monk_heal import run, setup

from game import monk


def test_a_civilization_with_heal_rate_heals_that_much_faster(monkeypatch):
    monkeypatch.setitem(civs.BY_KEY["heal_rate"], "ROMANS", 1.5)
    monkeypatch.setattr(civs, "civ", lambda g, player=None: "ROMANS")
    server, g = setup(("a", "MILITIA", 1, 8.5, 10.0, 40.0))
    run(g, 4)
    assert server.entities["a"]["Health"] == pytest.approx(10 + 4 * monk.RATE * 1.5)


def test_a_civilization_without_the_key_heals_at_the_rate_of_the_monk(monkeypatch):
    monkeypatch.setattr(civs, "civ", lambda g, player=None: None)
    server, g = setup(("a", "MILITIA", 1, 8.5, 10.0, 40.0))
    run(g, 4)
    assert server.entities["a"]["Health"] == pytest.approx(10 + 4 * monk.RATE)
