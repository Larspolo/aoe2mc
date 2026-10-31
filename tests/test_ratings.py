"""The Elo rating of each human player at the end of a game (#5166, epic #5165)."""
import json

import pytest

from game import ratings


class Fake:
    def __init__(self, sides=None, players=None):
        self.sent = []
        self.sides = sides or {}
        self.players = players or {}

    def command(self, cmd):
        self.sent.append(cmd)


def test_one_against_one_at_the_start_rating(tmp_path):
    path = tmp_path / "ratings.json"
    changes = ratings.update([(["Steve"], True), (["Alex"], False)], path)
    assert {n: round(new) for n, _, new in changes} == {"Steve": 1016, "Alex": 984}
    assert ratings.load(path) == pytest.approx({"Steve": 1016, "Alex": 984})


def test_a_team_game_changes_each_player_by_the_team_value(tmp_path):
    results = [(["Steve", "Bo"], True), (["Alex", "Cy"], False)]
    changes = ratings.update(results, tmp_path / "ratings.json")
    assert sorted((n, round(new - old)) for n, old, new in changes) == [
        ("Alex", -16), ("Bo", 16), ("Cy", -16), ("Steve", 16)]


def test_the_changes_of_a_game_sum_to_zero(tmp_path):
    path = tmp_path / "ratings.json"
    ratings.keep({"Steve": 1200, "Alex": 900, "Bo": 1100}, path)
    changes = ratings.update([(["Steve"], False), (["Alex", "Bo"], True)], path)
    assert sum(new - old for _, old, new in changes) == pytest.approx(0)
    changes = ratings.update([(["Steve"], True), (["Alex"], False), (["Bo"], False)], path)
    assert sum(new - old for _, old, new in changes) == pytest.approx(0)


def test_the_file_keeps_the_ratings_of_other_players(tmp_path):
    path = tmp_path / "ratings.json"
    ratings.keep({"Dee": 1234}, path)
    ratings.update([(["Steve"], True), (["Alex"], False)], path)
    table = json.loads(path.read_text(encoding="utf-8"))
    assert table["Dee"] == 1234 and set(table) == {"Dee", "Steve", "Alex"}


@pytest.mark.parametrize("results", [
    [(["Steve"], True)],                        # one human team: bots or one person
    [(["Steve"], False), (["Alex"], False)],    # no human team won: nothing to rate
])
def test_a_game_without_two_human_teams_changes_nothing(tmp_path, results):
    path = tmp_path / "ratings.json"
    assert ratings.update(results, path) == []
    assert not path.exists()


def test_teams_group_the_people_by_their_allies():
    players = {"1": {"team": 1}, "2": {"team": 1}, "3": {"team": 2}, "4": {}}
    g = Fake(sides={"Steve": 1, "Alex": 2, "Bo": 3, "Cy": 0}, players=players)
    assert ratings.teams(g, 1) == [(["Steve", "Alex"], True), (["Bo"], False)]


def test_announce_shows_each_change_in_the_chat():
    g = Fake()
    ratings.announce(g, [("Steve", 1000, 1016.0)])
    assert g.sent == ['tellraw @a {"translate": "aoe2mc.ratings.change", "fallback": "%s %s → %s", '
                      '"with": ["Steve", "1000", "1016"]}']
