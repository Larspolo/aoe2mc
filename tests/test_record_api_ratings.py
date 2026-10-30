"""tools/record_api.py ratings WORLD: the rating of each player with a profile goes into aoe2mc.json (#4669)."""
import io
import json
import urllib.error

from tools import record_api

META = {"tile_size": 4, "players": {"1": {"name": "Ann", "profile": 11}, "2": {"name": "Bob", "profile": 22},
                                    "3": {"name": "Cat"}}}


def world(tmp_path):
    (tmp_path / "aoe2mc.json").write_text(json.dumps(META))
    return tmp_path


def board(req):
    name = json.loads(req.data)["searchPlayer"]
    items = {"Ann": [{"rlUserId": 12, "elo": 900}, {"rlUserId": 11, "elo": 1234}], "Bob": [{"rlUserId": 22, "elo": 2000}]}
    return io.BytesIO(json.dumps({"items": items.get(name, [])}).encode())


def test_ratings_writes_the_rating_of_each_player_with_a_profile(tmp_path):
    record_api.ratings(str(world(tmp_path)), opener=board)
    got = json.loads((tmp_path / "aoe2mc.json").read_text())
    want = json.loads(json.dumps(META))
    want["players"]["1"].update(rating=1234, rating_now=True)
    want["players"]["2"].update(rating=2000, rating_now=True)
    assert got == want


def test_an_api_that_fails_gives_one_warning_line_and_no_rating(tmp_path, capsys):
    def fail(req):
        raise urllib.error.URLError("blocked")
    record_api.ratings(str(world(tmp_path)), opener=lambda req: board(req) if b"Ann" in req.data else fail(req))
    players = json.loads((tmp_path / "aoe2mc.json").read_text())["players"]
    assert players["1"]["rating"] == 1234 and "rating" not in players["2"] and "rating" not in players["3"]
    assert [line for line in capsys.readouterr().out.splitlines() if "warning" in line] == \
        ["warning: no rating of player 2: <urlopen error blocked>"]
