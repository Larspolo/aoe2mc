"""A saved game keeps the Recruitment Doctrines of the buildings, the targets of the attack orders and the fog toggle of
the cheat "polo" (#2537, epic #2253): after a load they are as before the save."""
import json

from test_loom import setup

from game import fog, savegame


def dumped(g):
    return json.loads(json.dumps(savegame.dump(g), sort_keys=True))


def test_a_loaded_game_has_the_doctrines_the_targets_and_the_fog_toggle():
    _, g = setup()
    g.doctrines = {"BARRACKS": 1}                                      # the second doctrine (train.switch)
    g.sieged.add("tower-uuid")
    g.reveal = "normal"
    assert fog.toggle(g) == "all"                                      # "polo"
    _, h = setup()
    h.reveal = "normal"                                                # the --reveal setting of the start (run.play)
    savegame.load(h, dumped(g))
    assert h.doctrines == {"BARRACKS": 1} and h.sieged == {"tower-uuid"} and h.reveal == "all"


def test_a_save_from_before_keeps_the_start_values():
    _, g = setup()
    d = dumped(g)
    for p in d["players"].values():
        for f in ("doctrines", "reveal", "sieged"):
            p.pop(f, None)
    _, h = setup()
    h.reveal = "normal"
    savegame.load(h, d)
    assert h.sieged == set() and h.reveal == "normal" and "doctrines" not in vars(h)
