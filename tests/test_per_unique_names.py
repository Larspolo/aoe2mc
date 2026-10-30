"""game/per.py: the my-unique-* names of the civilization of the bot, and the sets and classes in the counts (#4681).
The map of test_bot_gather: the bot is player 2."""
from test_per_players import script

import civs
import train
from game import per


def test_my_unique_names_give_the_items_of_the_civilization():
    s, b, me = script()
    civ, unit = next((c, u) for c, u in sorted(civs.UNIQUE.items()) if f"ELITE_{u}_UPGRADE" in {r["name"] for r in train.ROWS})
    b.g.data["players"]["2"]["civ"] = civ
    for name, part in (("my-unique-unit", "unit"), ("my-unique-unit-line", "unit"), ("my-elite-unique-unit", "elite")):
        assert per.names()[name]["civ"] == part
        assert s.game(name, "unit") == s.unique(part) and unit in s.game(name, "unit")
    assert s.game("my-unique-unit-upgrade", "tech") == f"ELITE_{unit}_UPGRADE"
    research = s.game("my-unique-research", "tech")
    assert train.value("civ", research) == civ and train.value("age", research) == 2


def test_no_civilization_gives_a_warning():
    s, b, me = script()
    b.g.data["players"]["2"].pop("civ", None)
    assert s.game("my-unique-unit", "unit") is None


def test_a_set_counts_each_of_its_units():
    s, b, me = script()
    row = next(r for r in per.names().values() if "set" in r)
    b.g.soldiers.update({f"s{i}": n for i, n in enumerate(row["set"] * 2)})
    n = 2 * len(row["set"])
    assert s.check(("unit-type-count", row["name"], "==", n)) and s.check(("unit-type-count-total", row["name"], "==", n))
    assert s.check(("players-unit-type-count", "any-enemy", row["name"], "==", 0))
