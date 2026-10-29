"""The aim of gunpowder units (the key "lead" of data/train.jsonl, Arquebus of the Portuguese, #4364): a researched
technology with the key tags the own units that its test matches, and its research tags the live ones. The test
technology is monkeypatched, so the test does not depend on the values of the data line."""
from test_train_castle import setup

import train as plain_train          # build imports train by its plain name (not game.train)
from game import train

TECH = "TEST_TECH"


def test_a_researched_technology_leads_the_shots_of_its_gunpowder_units(monkeypatch):
    monkeypatch.setitem(train.BY_KEY["lead"], TECH, {"if": [{"class": "gunpowder"}]})
    server, g = setup("PORTUGUESE", ages=3)
    assert train.lead_command(g, "u", "HAND_CANNONEER") is None     # no research, no tag
    g.techs.add(TECH)
    assert train.lead_command(g, "u", "HAND_CANNONEER") == "tag u add aoe2mc.lead"
    assert train.lead_command(g, "u", "ARCHER") is None


def test_a_research_tags_the_live_gunpowder_units_only(monkeypatch):
    monkeypatch.setitem(train.BY_KEY["lead"], TECH, {"if": [{"class": "gunpowder"}]})
    for m in (train, plain_train):
        monkeypatch.setitem(m.TECHS, TECH, lambda name, s: s)      # no values: the research only tags
    server, g = setup("PORTUGUESE", ages=3)
    g.soldiers.update({"gun": "HAND_CANNONEER", "bow": "ARCHER", "horse": "KNIGHT"})
    server.entities.update({u: {"Pos": (6.5, 64.0, 12.5)} for u in g.soldiers})
    server.log.clear()
    train.research(g, {"name": TECH, "player": 1}, start=True)
    tags = [c for c in server.log if c.startswith("tag ")]
    assert tags == ["tag gun add aoe2mc.lead"]
