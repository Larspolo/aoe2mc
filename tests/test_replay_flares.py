"""The flares of a record in the live replay (#2402, epic #2401): the bell, the light column of the game program
(game/flare.py) at the block of the tile for flare.SECONDS, and a chat line in the player color."""
import json
import os

import pytest
from test_replay import Fake, data

import aoe2mc
from game import flare, replay

RECORD = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "samples", "de-63.0.aoe2record")


def test_a_flare_shows_at_the_block_of_its_tile_with_the_bell_and_a_chat_line():
    r = replay.Replay(Fake(), data([]))
    out = r.commands({"time": 5000, "player": 2, "kind": "flare", "tile": [8.5, 3.25]})
    assert out[0] == f"playsound {flare.SOUND} master @a 34 70 13 1 1 1"
    assert out[1] == flare.particles(34, 70, 13, "@a", replay.FIREWORK_COLORS["orange"])
    assert json.loads(out[2][len("tellraw @a "):]) == [{"text": "<Player 2 (Aztecs)> ", "color": "gold"},
                                                       replay.say("flare", color="gold")]


def test_the_column_comes_again_until_the_flare_time_ends():
    r = replay.Replay(Fake(), data([]))
    r.commands({"time": 5000, "player": 1, "kind": "flare", "tile": [2.0, 2.0]})
    column = flare.particles(8, 70, 8, "@a", replay.FIREWORK_COLORS["blue"])
    assert column in r.expire(6000) and column in r.expire(5000 + flare.SECONDS * 1000 - 1)   # Replay.steps sends them
    assert column not in r.expire(5000 + flare.SECONDS * 1000) and r.flares == []


@pytest.mark.skipif(not os.path.isfile(RECORD), reason="no sample record")
def test_the_first_flare_of_a_record_shows_in_the_replay():
    e = next(e for e in aoe2mc.read_timeline(RECORD) if e["kind"] == "flare")
    assert (e["time"], e["player"]) == (422847, 2)
    out = replay.Replay(Fake(), data([], n=1024)).commands(e)
    x, z = (int(c * 4) for c in e["tile"])
    assert out[1] == flare.particles(x, 70, z, "@a", replay.FIREWORK_COLORS["orange"]) and "Flare" in out[2]
