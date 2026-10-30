"""The team bonuses (#4452): the key "team" of a civilization holds civilization keys that count for its player and each
ally (civs.civ gives a Team, civs.Table joins the values), not for an enemy and not with Full Tech Tree. Test data."""
import types

import pytest

from game import civs

ROWS = [{"name": "TEST_OWN", "work_rate": {"STABLE": [1.5, 1.5, 1.5, 1.5]}},
        {"name": "TEST_TEAM", "team": {"work_rate": {"STABLE": [1.2, 1.2, 1.2, 1.2], "DOCK": [2, 2, 2, 2]},
                                        "sight": {"HOUSE": 2}}},
        {"name": "TEST_OTHER", "team": {"work_rate": {"DOCK": [3, 3, 3, 3]}}}]


@pytest.fixture
def team(monkeypatch):
    monkeypatch.setattr(civs, "ROWS", ROWS)
    monkeypatch.setattr(civs, "TEAMS", {"TEST_TEAM", "TEST_OTHER"})
    monkeypatch.setattr(civs, "WORK_RATE", civs.Table("work_rate", lambda v: {b: tuple(f) for b, f in v.items()}))
    monkeypatch.setattr(civs, "SIGHT", civs.Table("sight"))


def game(player, full=False):
    players = {"1": {"civ": "TEST_OWN", "team": 1}, "2": {"civ": "TEST_TEAM", "team": 1},
               "3": {"civ": "TEST_OTHER", "team": 2}, "4": {"civ": "TEST_OWN"}}
    return types.SimpleNamespace(player=player, techs=set(), data={"players": players, "full_tech_tree": full})


def test_a_team_key_counts_for_the_player_and_its_allies(team):
    assert civs.work_rate(game(1), "STABLE") == pytest.approx(1.5 * 1.2)   # own and the ally: factors multiply
    assert civs.work_rate(game(1), "DOCK") == 2
    assert civs.work_rate(game(2), "STABLE") == pytest.approx(1.2)         # the player with the team bonus itself
    assert civs.SIGHT.get(civs.civ(game(1)), {}) == {"HOUSE": 2}
    assert civs.civ(game(1)) == "TEST_OWN" and civs.civ(game(1)).team == ("TEST_TEAM",)


def test_a_team_key_does_not_count_for_an_enemy_or_with_full_tech_tree(team):
    assert civs.work_rate(game(3), "STABLE") == 1 and civs.work_rate(game(3), "DOCK") == 3   # only its own team key
    assert civs.work_rate(game(4), "STABLE") == 1.5                        # no team: no ally
    assert civs.work_rate(game(4), "DOCK") == 1
    assert civs.work_rate(game(1, full=True), "STABLE") == 1 and civs.civ(game(1, full=True)) is None


def test_two_values_of_one_key_join():
    assert civs.join([("a", 1)], [("b", 2)]) == (("a", 1), ("b", 2))         # rule lists add up
    assert civs.join({"X": (1.5, 2)}, {"X": (2, 2), "Y": (3, 3)}) == {"X": (3.0, 4), "Y": (3, 3)}
    assert civs.join(1.1, 1.2) == pytest.approx(1.32) and civs.join(2, 4, add=True) == 6
    assert civs.join(None, {"A": 1}) == {"A": 1}


@pytest.mark.parametrize("rules", ["aoe2", "antiquity"])
def test_each_team_key_has_a_table_that_joins_it(rules):
    import table
    keys = {k for r in table.load("civs.jsonl", rules) for k in r.get("team", {})}
    assert keys <= civs.TEAM_KEYS, keys - civs.TEAM_KEYS
