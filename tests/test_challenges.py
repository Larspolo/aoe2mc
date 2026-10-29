"""game/challenge.py: the medal limits of the Art of War challenges (#3761)."""
from game import challenge


def limits(name):
    c = challenge.CHALLENGES[name]
    return c["gold"], c["silver"], c["bronze"]


def test_medal_of_a_time_challenge():
    g, s, b = limits("early-economy")
    assert [challenge.medal("early-economy", t) for t in (g - 1, g, g + 1, s, b, b + 1)] == \
        ["gold", "gold", "silver", "silver", "bronze", None]


def test_medal_of_a_battle_challenge_fewer_units_lost_is_better():
    g, s, b = limits("land-battle")
    assert [challenge.medal("land-battle", n) for n in (g, g + 1, s, s + 1, b, b + 1)] == \
        ["gold", "silver", "silver", "bronze", "bronze", None]
    assert challenge.limits("land-battle") == f"gold {g}, silver {s}, bronze {b} units lost"


def test_each_after_names_a_challenge_and_one_is_open_at_the_start():
    assert all(c["after"] in challenge.CHALLENGES for c in challenge.CHALLENGES.values() if c["after"])
    assert any(c["after"] is None for c in challenge.CHALLENGES.values())
