"""game/savegame.py: a save of the game program keeps the resources, technologies, age and population of each
player, and `game/run.py --load` goes on with it (#2255, epic #2253)."""
import json
import os

import pytest
from test_loom import setup

from game import run, savegame, train


def played():
    """A game after some play: resources, fractions, technologies (also an age and a repeated one), population."""
    server, g = setup(food=321, gold=45)
    g.stock.update(wood=77, stone=12)
    g.spare, g.seconds = {"food": 0.25}, {"gold": 0.5}
    g.techs.update({"FEUDAL_AGE", "LOOM", "DOUBLE_BIT_AXE"})
    g.repeats, g.pop = {"LOOM": 2}, 7
    g.clock = lambda: g.t0 + 60                     # a fixed game time: the save holds it (#3377), main red in #3601
    return server, g


def test_a_loaded_game_has_the_saved_resources_technologies_age_and_population():
    _, g = played()
    text = json.dumps(savegame.dump(g), sort_keys=True)
    server, h = setup()
    savegame.load(h, json.loads(text))
    for f in (*savegame.FIELDS, "techs"):
        assert getattr(h, f) == getattr(g, f), f
    assert train.age(h) == train.age(g) != train.age(setup()[1])
    assert f"scoreboard players set Wood {h.board} 77" in server.log      # the sidebar shows the loaded resources
    assert f"scoreboard players set Food {h.board} 321" in server.log


def test_the_same_game_gives_the_same_file():
    assert json.dumps(savegame.dump(played()[1])) == json.dumps(savegame.dump(played()[1]))


def test_a_save_has_a_copy_of_the_world_and_the_state(tmp_path):
    world = tmp_path / "World"
    (world / "region").mkdir(parents=True)
    (world / "level.dat").write_bytes(b"saved")
    (world / "session.lock").write_bytes(b"")
    state = savegame.dump(played()[1])
    path = savegame.write(str(tmp_path / "saves"), str(world), state)
    assert os.path.basename(path).startswith("World-")
    assert savegame.read(path) == json.loads(json.dumps(state))
    assert not os.path.exists(os.path.join(path, "world", "session.lock"))
    (world / "level.dat").write_bytes(b"played on")
    run.restore(os.path.join(path, "world"), str(world))                # what --load does before the server starts
    assert (world / "level.dat").read_bytes() == b"saved"


def test_run_has_the_load_option(capsys):
    with pytest.raises(SystemExit):
        run.main(["--help"])
    assert "--load SAVE" in capsys.readouterr().out
