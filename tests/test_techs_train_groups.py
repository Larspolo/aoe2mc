"""The key "train_group" of data/train.jsonl (#4260, Steppe Husbandry, Huaracas): a technology divides the train time of
the units of a group by its factor. Test data: a monkeypatched line of the key (owner, 2026-10-29, #4242)."""
import pytest
from test_train_castle import setup

from game import train

TECH = "LOOM"                                                       # train.seconds and train.stats need a real name


def times(g):
    return {n: train.seconds(g, n, b) for n, b in (("SCOUT_CAVALRY", "STABLE"), ("CAVALRY_ARCHER", "ARCHERY_RANGE"),
                                                    ("KNIGHT", "STABLE"), ("SLINGER", "ARCHERY_RANGE"),
                                                    ("ARCHER", "ARCHERY_RANGE"))}


def test_a_group_of_names_and_groups_trains_faster(monkeypatch):
    monkeypatch.setitem(train.BY_KEY["train_group"], TECH, [["scout line, steppe lancers", "CAVALRY_ARCHER"], 2])
    _, g = setup("BRITONS", ages=3)
    before = times(g)
    g.techs.add(TECH)
    after = times(g)
    assert after["SCOUT_CAVALRY"] == pytest.approx(before["SCOUT_CAVALRY"] / 2)
    assert after["CAVALRY_ARCHER"] == pytest.approx(before["CAVALRY_ARCHER"] / 2)
    assert after["KNIGHT"] == pytest.approx(before["KNIGHT"])


def test_a_group_trains_faster_and_its_effect_adds_range(monkeypatch):
    monkeypatch.setitem(train.BY_KEY["train_group"], TECH, ["slingers", 1.5])
    monkeypatch.setitem(train.TECHS, TECH, train.effect({"if": [{"names": ["SLINGER"]}], "add": {"range": 1}}))
    _, g = setup("BRITONS", ages=3)
    before, rng = times(g), train.stats(g, "SLINGER").range
    g.techs.add(TECH)
    after = times(g)
    assert after["SLINGER"] == pytest.approx(before["SLINGER"] / 1.5)
    assert after["ARCHER"] == pytest.approx(before["ARCHER"])
    assert train.stats(g, "SLINGER").range == rng + 1
