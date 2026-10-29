"""A saved game keeps the cheats that the player turned on (#2533, epic #2253): "aegis", "going above and beyond",
"tech tech one two free", "sharing is caring" and "my cpu can handle it" are on again after a load."""
import json

from test_loom import setup

from game import cheats, savegame, train

CHEATS = ("aegis", "beyond", "free_techs", "pop_cap", "sharing")       # the fields that the cheat codes set


def dumped(g):
    return json.loads(json.dumps(savegame.dump(g), sort_keys=True))


def test_a_loaded_game_has_each_cheat():
    _, g = setup()
    for code in ("aegis", "going above and beyond", "tech tech one two free", "sharing is caring", "my cpu can handle it"):
        cheats.CODES[code](g, "Steve")
    _, h = setup()
    savegame.load(h, dumped(g))
    assert {k: getattr(h, k) for k in CHEATS} == {k: getattr(g, k) for k in CHEATS}
    assert all(getattr(h, k) for k in CHEATS)
    assert train.max_pop(h) == train.max_pop(g) > train.max_pop(setup()[1])


def test_a_game_with_no_cheat_saves_no_cheat_key():
    _, g = setup()
    assert not set(savegame.CHEATS) & set(dumped(g)["players"]["1"])
