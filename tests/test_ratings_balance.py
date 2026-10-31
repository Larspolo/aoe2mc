"""The team balance by the Elo ratings (#5168): ratings.balance splits the players into two teams whose mean ratings
are near each other, and run.main refuses --balance with --teams."""
import pytest

from game import ratings, run


def test_balance_splits_by_mean_rating():
    teams = ratings.balance({"a": 1200, "b": 1100, "c": 1000, "d": 900})
    assert {n for n, t in teams.items() if t == 1} in ({"a", "d"}, {"b", "c"})
    assert {n for n, t in teams.items() if t == 2} == {"a", "b", "c", "d"} - {n for n, t in teams.items() if t == 1}


def test_balance_ties_take_the_first_split():
    table = {f"p{i}": 1000 for i in range(4)}                       # every split has the same difference
    first, again = ratings.balance(table), ratings.balance(dict(table))
    assert first == again
    assert first["p0"] == 1 and first["p1"] == 2                    # the first player is in team 1


def test_balance_one_or_two_players():
    assert ratings.balance({"a": 1000}) == {"a": 1}
    assert ratings.balance({"a": 1000, "b": 1400}) == {"a": 1, "b": 2}


def test_balance_eight_players_uses_both_teams():
    teams = ratings.balance({f"p{i}": 900 + 40 * i for i in range(8)})
    assert set(teams.values()) == {1, 2}
    assert len(teams) == 8


def test_balance_with_teams_stops(capsys):
    with pytest.raises(SystemExit) as e:
        run.main(["W", "--play", "--balance", "--teams", "1,2"])
    assert "--balance and --teams" in str(e.value)
