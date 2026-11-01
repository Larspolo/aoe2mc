"""The switch "Highlight huntable animals" of the Game menu (#5509): off by default; a click sends the plugin command
that makes the huntable animals of Gaia glow for that player only, a second click turns it off."""
from types import SimpleNamespace

from game import diplomacy, hunt_highlight


def fake(monkeypatch):
    monkeypatch.setattr(hunt_highlight.gather, "HUNT_FOOD", {"PREY_A": 100, "PREY_B": 300})
    log = []
    g = SimpleNamespace(command=lambda c: log.append(c) or "", menus={}, game=None, players={},
                        prey={"u1": "PREY_A", "u2": "PREY_B", "u3": "WOLFISH", "u4": "PREY_A", "u5": "PREY_A"},
                        dead={"u4": (0, 0)}, flock={"u5"})
    return g, log


def test_default_is_off(monkeypatch):
    g, log = fake(monkeypatch)
    assert not hunt_highlight.on(g, "Steve")
    assert "off" in hunt_highlight.button(g, "Steve")[2]


def test_toggle_glows_for_one_player(monkeypatch):
    g, log = fake(monkeypatch)
    assert hunt_highlight.toggle(g, "Steve")
    assert log == ["aoe huntglow Steve on u1 u2"]              # no predator, dead animal or own herdable
    assert not hunt_highlight.on(g, "Alex")
    assert not hunt_highlight.toggle(g, "Steve")
    assert log[-1] == "aoe huntglow Steve off"


def test_long_list_splits(monkeypatch):
    out = hunt_highlight.commands("Steve", [f"{i:036d}" for i in range(10)], limit=120)
    assert out[0].startswith("aoe huntglow Steve on ") and all(c.startswith("aoe huntglow Steve add ") for c in out[1:])
    assert all(len(c) <= 120 for c in out) and sum(len(c.split()) - 4 for c in out) == 10


def test_game_menu_button(monkeypatch):
    g, log = fake(monkeypatch)
    diplomacy.button(g, "Steve", diplomacy.HUNT_SLOT)
    assert "aoe huntglow Steve on u1 u2" in log and hunt_highlight.on(g, "Steve")
