"""Live replay: the ships of a dock appear on the water and sail only on the water (#866). Fake RCON."""
import contextlib
import io
import json
import math
import os
import re
import sys

import pytest

import aoe2mc

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "game"))
import replay  # noqa: E402
from test_replay_spawn import REC, queue, summons  # noqa: E402
from test_replay_walk import HOUSE, play  # noqa: E402

N = 64
WATER = {(x, z) for x in range(N) for z in range(40, N)}                # the sea south of z = 40
DOCK = {"kind": "building", "name": "DOCK", "player": 1, "ref": 11, "tile": [5.5, 10.0], "footprint": [16, 36, 28, 44]}
FISH = {"kind": "other", "name": "FISH_SALMON", "ref": 12, "tile": [12.5, 13.5]}
SHIP = dict(player=1, objects=[900], names=["FISHING_SHIP"])


def ship(*events):
    """Replay a dock that trains a fishing ship at 0 (ready at 1:00), then the events."""
    return play([queue(t=0, objects=[11], name="FISHING_SHIP", type=13)] + list(events), (DOCK, FISH, HOUSE),
                n=N, water=WATER)


def sails(sent):
    """The cells of the /tp steps of the ships."""
    return [(math.floor(float(m[1])), math.floor(float(m[2]))) for c in sent
            if (m := re.match(r"execute as \S+ at @s run tp @s (\S+) ~ (\S+) ", c))]


def test_a_dock_puts_its_fishing_ship_on_the_water():
    r, sent, _ = ship()
    (kind, x, y, z), = summons(sent)
    assert kind == "minecraft:oak_boat" and (math.floor(x), math.floor(z)) in WATER
    assert not (16 <= x < 28 and 36 <= z < 44)                       # not in the dock
    assert y == 69                                                   # one block under the shore (y 70)


def test_a_ship_sails_on_the_water_to_a_tile_on_land():
    r, sent, _ = ship(dict(time=70000, kind="move", tile=[8.5, 9.5], **SHIP))   # a land tile 2 tiles from the sea
    cells = sails(sent)
    assert cells and set(cells) <= WATER and not [c for c in sent if c.startswith("tp ")]
    assert all(math.dist(a, b) <= 1.5 for a, b in zip(cells, cells[1:]))
    assert cells[-1] == (34, 40)                                     # the water cell nearest to block (34, 38)


def test_an_order_takes_the_ship_next_to_its_fish():
    r, sent, _ = ship(dict(time=70000, kind="order", target=12, tile=[12.5, 13.5], **SHIP))
    x, z = sails(sent)[-1]
    assert (x, z) in WATER and max(abs(x - 49.5), abs(z - 53.5)) <= 3    # next to the 4 × 4 cells of the fish


def test_an_order_on_land_gives_a_target_on_the_water_or_none():
    r, sent, _ = ship(dict(time=70000, kind="order", target=9, tile=[6.0, 10.0], **SHIP))   # the house, far inland
    assert set(sails(sent)) <= WATER


@pytest.mark.slow
def test_sample_record_ships_stay_on_the_water(tmp_path):
    """The sample record to 15:00 offline: no fishing ship appears or sails on a land cell."""
    pytest.importorskip("mgz.model")
    with contextlib.redirect_stdout(io.StringIO()):
        aoe2mc.convert(REC, str(tmp_path / "W"))
    with open(tmp_path / "W" / "aoe2mc.json") as f:
        d = json.load(f)
    d["timeline"] = [e for e in d["timeline"] if e["time"] <= 15 * 60000]
    sent, now = [], [0.0]

    class Game:
        def command(self, cmd):
            sent.append(cmd)
            return ""

    def sleep(s):
        now[0] += s
    r = replay.Replay(Game(), d)
    r.run(speed=1000, clock=lambda: now[0], sleep=sleep, log=None)
    m = r.map
    boats = [(math.floor(x), math.floor(z)) for k, x, _, z in summons(sent) if k.endswith("_boat")]
    assert len(boats) >= 5 and all(m.ground[z][x] is None for x, z in boats)
    cells = sails(sent)
    assert cells and all(m.ground[z][x] is None for x, z in cells)
