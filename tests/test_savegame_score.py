"""A saved game keeps the counts of the AoE2 score (#2475, epic #2253): the losses, the razed buildings, the free
units, the tributes and the units that gave their spoils. After a load the score is the score at the save."""
import json

from test_gather import FakeServer, grid

from game import gather, savegame, score

KEYS = ("fallen", "given", "losses", "razed", "tributes")


def setup():
    """A flat 24 × 24 map (tile size 1) with a town center of player 1."""
    objects = [{"kind": "building", "name": "TOWN_CENTER", "player": 1, "tile": [3.5, 3.5], "footprint": [2, 2, 5, 5]}]
    return gather.Gather(FakeServer({}), grid([[64] * 24 for _ in range(24)], objects)).setup()


def played():
    g = setup()
    g.losses = {"dead-1": "KNIGHT", "dead-2": "VILLAGER"}
    g.razed = {"fort-1": "CASTLE"}
    g.given = {"MAN_AT_ARMS_UPGRADE"}
    g.techs.add("MAN_AT_ARMS_UPGRADE")
    g.tributes = {2: {"food": 100, "gold": 0, "stone": 0, "wood": 200}}
    g.fallen = {"dead-1", "dead-2"}
    return g


def test_a_loaded_game_keeps_the_counts_and_the_score():
    g = played()
    h = setup()
    savegame.load(h, json.loads(json.dumps(savegame.dump(g), sort_keys=True)))
    assert {k: vars(h).get(k) for k in KEYS} == {k: vars(g)[k] for k in KEYS}
    assert score.points(h) == score.points(g)


def test_a_save_without_the_counts_loads():
    g = setup()
    d = savegame.dump(g)
    assert set(KEYS) & set(d["players"]["1"]) == set(KEYS) & set(vars(g))   # only the fields that the Gather has
    for p in d["players"].values():                                    # a save from before #2475
        for k in KEYS:
            p.pop(k, None)
    h = setup()
    savegame.load(h, json.loads(json.dumps(d, sort_keys=True)))
    assert score.points(h) == score.points(g)
