"""game/challenge.py: the medal limits of the Art of War challenges (#3761)."""
from game import challenge


def test_medal_of_a_time_challenge():
    assert [challenge.medal("early-economy", s) for s in (300, 480, 481, 600, 780, 781)] == \
        ["gold", "gold", "silver", "silver", "bronze", None]


def test_medal_of_a_battle_challenge_fewer_units_lost_is_better():
    assert [challenge.medal("land-battle", n) for n in (0, 1, 5, 6, 10, 11)] == \
        ["gold", "silver", "silver", "bronze", "bronze", None]
    assert challenge.limits("land-battle") == "gold 0, silver 5, bronze 10 units lost"


def test_nine_challenges_and_each_after_names_one_of_them():
    assert len(challenge.CHALLENGES) == 9
    assert all(c["after"] in challenge.CHALLENGES for c in challenge.CHALLENGES.values() if c["after"])
    assert sum(c["after"] is None for c in challenge.CHALLENGES.values()) == 4          # 4 are open at the start
