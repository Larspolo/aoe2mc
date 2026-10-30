"""The team key "hp" (#4790): a factor of the hit points of a building for the player and each ally (Antiquity Mode:
the Macedonian houses). Test data: the civilization lines of the test, not the data file."""
import types

import pytest

from game import civs, combat

ROWS = [{"name": "TEST_OWN"},
        {"name": "TEST_TEAM", "team": {"hp": {"HOUSE": 2}}},
        {"name": "TEST_OTHER", "team": {"hp": {"HOUSE": 3}}}]


@pytest.fixture
def team(monkeypatch):
    monkeypatch.setattr(civs, "ROWS", ROWS)
    monkeypatch.setattr(civs, "TEAMS", {"TEST_TEAM", "TEST_OTHER"})
    monkeypatch.setattr(civs, "HP", civs.Table("hp"))


def game(player):
    players = {"1": {"civ": "TEST_OWN", "team": 1}, "2": {"civ": "TEST_TEAM", "team": 1},
               "3": {"civ": "TEST_OTHER", "team": 2}, "4": {"civ": "TEST_OWN"}}
    return types.SimpleNamespace(player=player, techs=set(), data={"players": players})


def test_a_team_hp_factor_counts_for_the_player_and_its_ally(team):
    base = combat.stats("HOUSE")
    assert civs.hp(civs.civ(game(1)), "HOUSE", base).hp == 2 * base.hp   # the ally: 2 times, not the enemy's 3
    assert civs.hp(civs.civ(game(2)), "HOUSE", base).hp == 2 * base.hp   # the player with the team bonus itself


def test_a_player_without_an_ally_gets_the_base_hit_points(team):
    base = combat.stats("HOUSE")
    assert civs.hp(civs.civ(game(4)), "HOUSE", base) == base


def test_with_team_names_the_allies_of_a_player_in_the_combat_setup(team):
    players = game(1).data["players"]
    assert civs.with_team("TEST_OWN", players, 1).team == ("TEST_TEAM",)
    assert civs.with_team("TEST_OWN", players, 4) == "TEST_OWN"
    assert civs.with_team(None, players, 1) is None
