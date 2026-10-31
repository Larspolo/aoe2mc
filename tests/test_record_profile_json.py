"""aoe2mc.json of a record keeps the profile ID of each player (#5002): `record_api.py ratings` finds the ratings by it."""
import json

from mgz.model import parse_match

import aoe2mc

RECORD = "samples/de-64.3.aoe2record"


def test_aoe2mc_json_has_the_profile_of_each_player(tmp_path):
    aoe2mc.convert(RECORD, str(tmp_path / "w"))
    players = json.load(open(tmp_path / "w" / "aoe2mc.json"))["players"]
    with open(RECORD, "rb") as f:
        match = parse_match(f)
    for p in match.players:
        assert players[str(p.number)]["profile"] == p.profile_id > 0
    assert "profile" not in players["0"]
