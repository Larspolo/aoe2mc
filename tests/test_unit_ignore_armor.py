"""The key "ignore_armor" of a line of data/units.jsonl (#4394): the hits of that unit ignore the armor of the target,
as the Leitis of AoE2 DE. The rule of train.hits reads the set combat.IGNORE, as the Wootz Steel rule (#4331) does."""
import combat, train   # the modules that train.hits imports (game/ on the path, as the other tests of the rule)

from test_train_castle import setup


def test_a_unit_with_the_key_ignore_armor_ignores_the_armor_of_its_target(monkeypatch):
    monkeypatch.setattr(combat, "IGNORE", {"KNIGHT"})
    _, g = setup("DRAVIDIANS", ages=3)                             # no research
    assert train.hits(g, "KNIGHT")["ignore"]
    assert not train.hits(g, "CHAMPION")["ignore"]
