"""Save version 68.9 (#5178): the lobby block is the last part of the header, after a block of the XS state that mgz
1.8.51 does not know. new_saves finds it by the map size and the population limit of the header."""
import os

import pytest

import aoe2mc

SAMPLES = os.path.join(os.path.dirname(__file__), os.pardir, "samples")
RECORD = os.path.join(SAMPLES, "de-regicide.aoe2record")      # save 68.9, Regicide, Tiny map, population 200
SAVE = os.path.join(SAMPLES, "aoe2mc-sample.aoe2spgame")      # save 68.9 (PR #4705)


def test_the_lobby_of_a_record_of_save_68_9_reads():
    from mgz.model import parse_match
    aoe2mc.new_saves()
    with open(RECORD, "rb") as f:
        match = parse_match(f)
    assert (match.population, match.lock_teams) == (200, True)   # all zeros before #5178


def test_the_sample_save_of_68_9_reads_its_players_and_resources():
    if not os.path.exists(SAVE):
        pytest.skip("no sample save")
    players = aoe2mc.read_saved(SAVE)[6]
    assert [n for n in players if n] == [1, 2]
    assert all(players[n]["saved"] and players[n]["age"] for n in (1, 2))
    assert all(sum(players[n]["resources"].values()) > 0 for n in (1, 2))
