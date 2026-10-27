"""The bonus keys of game/data/civs.jsonl and the unit groups of game/data/units.jsonl (#2031): the form of the data,
not a copy of its values."""
from game import civs, combat, gather, table, train


def test_the_unit_groups_are_groups_of_the_bonuses():
    rows = [r for r in table.load("units.jsonl") if "groups" in r]
    assert rows and all(r["groups"] == sorted(set(r["groups"])) and set(r["groups"]) <= set(civs.GROUPS) for r in rows)
    assert list(civs.GROUPS) == sorted(civs.GROUPS)
    assert civs.GROUPS["archer line"]("ARCHER", combat.STATS["ARCHER"])            # a group of names
    assert civs.GROUPS["barracks"]("CONDOTTIERO", combat.STATS["CONDOTTIERO"])     # a rule and a name
    assert not civs.GROUPS["foot archers but skirmishers"]("SKIRMISHER", combat.STATS["SKIRMISHER"])


def test_the_civilization_bonuses_have_known_names():
    kinds = {"farm", "food", "gold", "hunt", "sheep", "stone", "wood"}
    assert all(set(w) <= kinds and all(isinstance(f, float) for f in w.values()) for w in civs.WORK.values())
    assert all(set(b) <= set(gather.START) for b in civs.START.values())
    known = set(train.COSTS) | set(combat.STATS)
    assert set(civs.SHARED) <= known and set(civs.NOT_SHARED) <= set(civs.SHARED)
    assert all(g in civs.GROUPS and isinstance(up, bool) for b in civs.TRAIN_RATE.values() for g, _, up in b)
    assert all(len(v) == 4 for r in civs.WORK_RATE.values() for v in r.values())
    assert set(b for r in civs.HP.values() for b in r) <= set(train.build.COSTS)


def test_the_technology_groups_are_menu_items():
    assert civs.SMITH and set(civs.SMITH) == set(train.TRAINS["BLACKSMITH"]) & set(train.TECHS)
    assert civs.ECONOMY and set(civs.ECONOMY) <= set(train.TECHS) and "COINAGE" not in civs.ECONOMY
