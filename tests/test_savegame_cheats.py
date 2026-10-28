"""A saved game keeps the cheats that the player turned on (#2533, epic #2253): "aegis", "going above and beyond",
"tech tech one two free", "sharing is caring" and "my cpu can handle it" are on again after a load."""
import json

from test_loom import setup

from game import cheats, savegame, train

CHEATS = {"aegis": True, "beyond": True, "free_techs": True, "pop_cap": 1000, "sharing": True}


def dumped(g):
    return json.loads(json.dumps(savegame.dump(g), sort_keys=True))


def test_a_loaded_game_has_each_cheat():
    _, g = setup()
    for code in ("aegis", "going above and beyond", "tech tech one two free", "sharing is caring", "my cpu can handle it"):
        cheats.CODES[code](g, "Steve")
    _, h = setup()
    savegame.load(h, dumped(g))
    assert {k: getattr(h, k) for k in CHEATS} == CHEATS
    assert train.max_pop(h) == 1000


def test_a_game_with_no_cheat_saves_no_cheat_key():
    _, g = setup()
    assert not set(savegame.CHEATS) & set(dumped(g)["players"]["1"])
