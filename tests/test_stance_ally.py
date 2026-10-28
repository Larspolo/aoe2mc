"""#2997: an ally with no team joins the team of the player that makes the alliance. The other allies of that player
keep their alliance, and both directions of an alliance give the same teams."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "game"))
import gather  # noqa: E402
import scenario  # noqa: E402


def players():
    return {"1": {"team": 1}, "2": {}, "3": {"team": 1}}


def test_ally_with_no_team_keeps_the_alliance_of_the_maker():
    p = players()
    scenario.stance(p, 1, 2, "ally")
    assert gather.allied(p, 1, 3)
    assert gather.allied(p, 1, 2)


def test_both_directions_give_the_same_teams():
    one, two = players(), players()
    scenario.stance(one, 1, 2, "ally")
    scenario.stance(two, 2, 1, "ally")
    assert {k: v.get("team") for k, v in one.items()} == {k: v.get("team") for k, v in two.items()}


def test_two_players_with_no_team_get_one_new_team():
    p = {"1": {}, "2": {}, "3": {"team": 1}}
    scenario.stance(p, 1, 2, "ally")
    assert p["1"]["team"] == p["2"]["team"] != 1
    assert not gather.allied(p, 1, 3)


def test_a_player_with_a_team_moves_to_the_team_of_an_ally_with_a_team():
    p = {"1": {"team": 1}, "2": {"team": 2}}
    scenario.stance(p, 1, 2, "ally")
    assert p["1"]["team"] == p["2"]["team"] == 2
