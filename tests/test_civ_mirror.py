"""--civ-mode mirror and team-random: the AoE2 lobby options "Mirror" and "Team Random" (#4757)."""
from game import civs, run


def _data():
    return {"map_size": 120, "objects": [{}] * 7, "players": {
        "0": {"civ": "GAIA"}, "1": {"civ": "FRANKS", "team": 1}, "2": {"civ": "BRITONS", "team": 2},
        "3": {"civ": "MONGOLS", "team": 1}, "4": {"civ": "CELTS", "team": 2, "lock_civ": True}}}


def _civ(data, k):
    return data["players"][k]["civ"]


def test_mirror_gives_all_players_the_civilization_of_player_1():
    data = _data()
    run.apply_civ_mode(data, "mirror")
    assert [_civ(data, k) for k in "123"] == ["FRANKS"] * 3
    assert _civ(data, "4") == "CELTS" and _civ(data, "0") == "GAIA"


def test_mirror_of_random_gives_one_known_civilization_to_all():
    data = _data()
    data["players"]["1"]["civ"] = "RANDOM"
    run.apply_civ_mode(data, "mirror")
    assert len({_civ(data, k) for k in "123"}) == 1
    assert _civ(data, "1") in {r["name"] for r in civs.ROWS}


def test_team_random_gives_each_team_one_civilization_deterministically():
    a, b = _data(), _data()
    run.apply_civ_mode(a, "team-random")
    run.apply_civ_mode(b, "team-random")
    assert _civ(a, "1") == _civ(a, "3") in {r["name"] for r in civs.ROWS}
    assert _civ(a, "4") == "CELTS"
    assert a == b


def test_normal_changes_nothing():
    data = _data()
    run.apply_civ_mode(data, "normal")
    assert data == _data()
