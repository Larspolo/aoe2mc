"""game/train.py: the key "on_research" of a technology line in game/data/train.jsonl names the functions that run at
its research, with (g, entry): a special effect is a function in its own module, not an if block of train.research()
(#3243)."""
import sys
import types

from test_tower_upgrades import setup

from game import train


def test_research_calls_each_function_of_the_key_once(monkeypatch):
    calls = []
    monkeypatch.setitem(sys.modules, "x_hook", types.SimpleNamespace(f=lambda g, entry: calls.append((g, entry))))
    monkeypatch.setitem(train.BY_KEY["on_research"], "LOOM", ["x_hook.f"])
    server, g = setup()
    entry = {"name": "LOOM", "player": "Steve"}
    train.research(g, entry)
    assert calls == [(g, entry)]


def test_a_technology_without_the_key_calls_nothing(monkeypatch):
    monkeypatch.setitem(sys.modules, "x_hook", types.SimpleNamespace(f=lambda g, entry: 1 / 0))
    server, g = setup()
    train.research(g, {"name": "LOOM", "player": "Steve"})
    assert "LOOM" in g.techs

