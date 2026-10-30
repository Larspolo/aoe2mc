"""The flare column of the live replay in the player color (#2442, epic #2401): dust particles of the RGB of the
player color, also in the repeats of expire; the game program keeps its end_rod column (owner decision #1232)."""
import pytest
from test_replay import Fake, data

from game import flare, replay


def column(out):
    return [c for c in out if c.startswith("particle ")]


def test_the_flares_of_a_blue_and_an_orange_player_have_their_colors():
    r = replay.Replay(Fake(), data([]))
    blue = column(r.commands({"time": 0, "player": 1, "kind": "flare", "tile": [2.0, 2.0]}))
    orange = column(r.commands({"time": 0, "player": 2, "kind": "flare", "tile": [3.0, 3.0]}))
    assert blue == ["particle minecraft:dust{color:[0.15,0.19,0.57],scale:2} 8.5 74 8.5 0.1 4 0.1 0 40 force @a"]
    assert orange[0].startswith("particle minecraft:dust{color:[0.92,0.53,0.27],scale:2} 12.5 ")
    assert sorted(column(r.expire(1000))) == sorted(blue + orange)      # the repeats keep the color


def test_the_game_program_keeps_the_end_rod_column():
    assert flare.particles(1, 2, 3, "@a").startswith("particle minecraft:end_rod 1.5 6 3.5 ")


@pytest.mark.mc
def test_the_colored_column_runs_on_a_server(tmp_path):
    from test_mc_check import mojang_reachable
    if not mojang_reachable():
        pytest.skip("Mojang is not reachable")
    import contextlib
    import io

    import scenarios

    import aoe2mc
    from game import run
    src = str(tmp_path / "flare.aoe2scenario")
    scenarios.save(scenarios.new_scenario(16), src)
    with contextlib.redirect_stdout(io.StringIO()):
        aoe2mc.convert(src, str(tmp_path / "W"))
    with run.Game(tmp_path / "W") as game:
        game.forceload()
        out = [game.command(flare.particles(8, 64, 8, "@a", replay.FIREWORK_COLORS[c])) for c in ("blue", "orange")]
    assert not [o for o in out if any(w in o for w in ("Unknown", "Incorrect", "Expected", "Invalid", "Malformed"))]
