"""The melee splash of a technology (#4496: Druzhina, Logistica, Vendel Legacy, Lechitic Legacy): the key "trample" of
data/train.jsonl with the blast radius of the unit, train.trample_command and `aoe trample` of the plugin.
Test data, not the data lines (owner, 2026-10-29, #4242). Fake server."""
import pytest
from test_dock_train import dock_map

import train as plain_train          # build and gather import train by its plain name (not game.train)
from game import train

EFFECT = {"if": [{"names": ["MILITIA"]}], "add": {"blast": 0.5}}


@pytest.fixture
def tech(monkeypatch):
    for module in (plain_train, train):
        monkeypatch.setitem(module.BY_KEY["trample"], "TEST_FLAT", {"damage": 5})
        monkeypatch.setitem(module.BY_KEY["trample"], "TEST_PART", {"part": 0.33})
        for name in ("TEST_FLAT", "TEST_PART"):
            monkeypatch.setitem(module.BY_KEY["effect"], name, EFFECT)
            monkeypatch.setitem(module.TECHS, name, module.effect(EFFECT))
    return dock_map()


@pytest.mark.parametrize("name, tail", [("TEST_FLAT", "0 {r:g} 5 0"), ("TEST_PART", "0.33 {r:g}")])
def test_a_melee_unit_of_the_research_gets_the_splash(tech, name, tail):
    server, g = tech
    g.techs.add(name)
    assert train.trample_command(g, "u", "MILITIA") == "aoe trample u " + tail.format(r=0.5 * g.map.T)   # the blast in blocks
    assert train.trample_command(g, "u", "ARCHER") is None


def test_with_no_research_no_splash(tech):
    server, g = tech
    assert train.trample_command(g, "u", "MILITIA") is None


def test_the_research_gives_the_live_units_the_splash(tech):
    server, g = tech
    uuid = train.summon(g, "MILITIA", (5.5, 64.0, 12.5))
    archer = train.summon(g, "ARCHER", (6.5, 64.0, 12.5))
    assert not any(c.startswith("aoe trample") for c in server.log)
    del server.log[:]
    train.research(g, {"name": "TEST_FLAT", "player": 1}, start=True)
    assert f"aoe trample {uuid} 0 {0.5 * g.map.T:g} 5 0" in server.log
    assert not any(c.startswith(f"aoe trample {archer}") or c in ("0", "None") for c in server.log)
    later = train.summon(g, "MILITIA", (7.5, 64.0, 12.5))
    assert f"aoe trample {later} 0 {0.5 * g.map.T:g} 5 0" in server.log
