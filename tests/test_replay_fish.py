"""Live replay: a fishing ship with an ORDER on a fish, and a villager at a shore fish, get its food at the AoE2 rate,
live and in a jump (#1283). Fake clock and RCON."""
import os
import sys
import types

import pytest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from test_replay import data  # noqa: E402
from test_replay_control import Clock  # noqa: E402
from test_replay_ships import DOCK, FISH, SHIP, WATER  # noqa: E402
from test_replay_spawn import queue  # noqa: E402

import gather  # noqa: E402
import replay  # noqa: E402

N, END = 64, 300000
SHORE = {"kind": "other", "name": "SHORE_FISH", "ref": 13, "tile": [3.5, 10.5]}   # next to the land (z < 40)


def play(timeline, to=None):
    """Replay a dock that trains a fishing ship at 0 (ready at 1:00), then the timeline, up to END."""
    d = data([queue(t=0, objects=[11], name="FISHING_SHIP", type=13)] + timeline
             + [dict(time=END + 1000, player=1, kind="chat", text="end")], n=N)
    d["ground"] = [" ".join("-" if (x, z) in WATER else "70" for x in range(N)) for z in range(N)]
    d["objects"] += [DOCK, FISH, SHORE]
    game = Clock()
    r = replay.Replay(game, d)
    r.run(clock=lambda: game.now, sleep=game.sleep, log=None, to=to)
    return r


@pytest.mark.parametrize("jump", [False, True])
def test_a_fishing_ship_with_an_order_on_a_fish_gets_its_food(jump):
    r = play([dict(time=70000, kind="order", target=12, tile=[12.5, 13.5], **SHIP)], to=END if jump else None)
    food, rate = r.gathered.get(1, {}).get("food", 0), gather.SHIP_WORK["deep"]
    assert rate * (END - 70000 - 20000) / 1000 <= food <= rate * (END - 70000) / 1000, food
    if not jump:                                                       # live: the fish loses its food
        assert r.map.fish[(12, 13)] == gather.FISH_FOOD["FISH_SALMON"] - food


def test_the_map_knows_the_fish_and_its_food():
    r = play([])
    assert r.map.fish == {(12, 13): gather.FISH_FOOD["FISH_SALMON"], (3, 10): gather.FISH_FOOD["SHORE_FISH"]}
    assert r.map.shore == {(3, 10)}
    assert r.map.resource((12, 13)) == "food" and gather.job_of(r.map, (3, 10)) == "FISHERMAN"


def test_the_rates_of_a_fisherman_and_a_fishing_ship():
    r = play([])
    rate = lambda name, tile: r.rate(types.SimpleNamespace(name=name, tree=tile))   # noqa: E731
    assert rate("VILLAGER_MALE", (3, 10)) == gather.AOE2_WORK["fish"]
    assert rate("FISHING_SHIP", (3, 10)) == gather.SHIP_WORK["shore"] and rate("FISHING_SHIP", (12, 13)) == gather.SHIP_WORK["deep"]


def test_a_move_gives_a_fishing_ship_no_work():
    r = play([dict(time=70000, kind="move", tile=[12.5, 13.5], **SHIP)])
    assert r.units[900].tree is None and not r.gathered.get(1, {}).get("food")
