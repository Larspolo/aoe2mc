"""--civ-pool: Random picks only from the civilizations that the host enables (#4756)."""
import pytest

from game import civs, run


def _names():
    return sorted(r["name"] for r in civs.ROWS)


def test_random_picks_only_from_the_pool():
    pool = run.civ_pool_choice(f"{_names()[0].lower()}, {_names()[-1]}")
    assert pool == [_names()[0], _names()[-1]]
    for player in range(1, 9):
        data = {"map_size": 120, "objects": [], "players": {}}
        run.apply_civs(data, {player: "RANDOM"}, pool)
        assert data["players"][str(player)]["civ"] in pool


def test_an_unknown_name_stops_with_the_list():
    with pytest.raises(SystemExit) as e:
        run.civ_pool_choice(f"{_names()[0]},NOCIV")
    assert _names()[1] in str(e.value)

