"""Live replay: the buildings that the replay places show on the map item as squares in the player color, and a
deleted one goes away (#1238, Minimap.java of the plugin). Fake RCON, and the commands on a real Paper server."""
import os
import re
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "game"))
import replay  # noqa: E402
from test_replay import Fake, data  # noqa: E402
from test_replay_delete import delete  # noqa: E402

import aoe2mc  # noqa: E402

HOUSE = dict(time=0, player=1, kind="build", type=70, name="HOUSE", tile=[12.0, 4.0])


def minimap(cmds):
    return [c for c in cmds if c.startswith("aoe minimap ")]


def test_a_build_sends_its_footprint_and_team_and_a_delete_removes_it():
    r = replay.Replay(Fake(), data([]), ai=True)
    built = minimap(r.commands(HOUSE))
    x0, x1, z0, z1 = r.placed[-1][2]
    assert built == [f"aoe minimap building {x0} {z0} {x1} {z1} p1"]
    assert minimap(r.commands(delete(500, [900], names=["HOUSE"]))) == [f"aoe minimap unbuild {x0} {z0}"]


def test_without_the_plugin_no_minimap_commands():
    r = replay.Replay(Fake(), data([]))
    assert r.commands(HOUSE) and not minimap(r.commands(HOUSE))
    assert not minimap(r.commands(delete(500, [900], names=["HOUSE"])))


@pytest.mark.mc
def test_the_building_commands_on_a_server(tmp_path):
    from test_paper import paper_reachable
    if not paper_reachable():
        pytest.skip("Paper is not reachable")
    from game import run
    world = str(tmp_path / "W")
    aoe2mc.convert(aoe2mc.RANDOM_MAP + "arabia", world)               # the teams p1 and p2 with their colors
    with run.Game(world) as game:
        game.forceload()
        assert "Minimap: on" in game.command("aoe minimap on")
        game.command("give @a minecraft:filled_map[minecraft:map_id=0]")
        out = [game.command("aoe minimap building 100 120 108 128 p1"), game.command("aoe minimap building 0 0 8 8 p9")]
        assert "Minimap buildings: 1" in out[0] and "Minimap buildings: 2" in out[1]   # p9: no team, gray
        game.command("tick sprint 40")                                 # the renderer runs on the server ticks
        out += [game.command("aoe minimap unbuild 100 120")]
        assert "Minimap buildings: 1" in out[-1]
        assert not re.search(r"(?i)exception|error|unknown", " ".join(out + [game.command("aoe minimap off")]))
