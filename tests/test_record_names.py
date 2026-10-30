"""The player names and profile IDs of a recorded game (#4667): the replay shows them."""
from mgz.model import parse_match

from aoe2mc import read_record

RECORD = "samples/de-64.3.aoe2record"


def test_record_players_have_names_and_profiles():
    players = read_record(RECORD)[6]
    with open(RECORD, "rb") as f:
        match = parse_match(f)
    for p in match.players:
        assert isinstance(players[p.number]["name"], str) and players[p.number]["name"] == p.name != ""
        assert isinstance(players[p.number]["profile"], int) and players[p.number]["profile"] == p.profile_id


def test_gaia_has_no_name_or_profile():
    players = read_record(RECORD)[6]
    assert "name" not in players[0] and "profile" not in players[0]
