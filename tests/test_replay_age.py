"""Live replay: an age-up shows fireworks in the player color at the town center of the player (#844)."""
import os
import re
import shutil
import sys
import time

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "game"))
import replay  # noqa: E402
from test_replay import Fake, data  # noqa: E402
from test_replay_spawn import TC  # noqa: E402

AGE = {"time": 1, "player": 1, "kind": "age", "age": "FEUDAL_AGE"}


def rockets(cmds):
    return [c for c in cmds if c.startswith("summon minecraft:firework_rocket ")]


def test_age_up_gives_fireworks_in_the_player_color_at_the_town_center():
    d = data([])
    d["objects"].append(TC)                                    # footprint x 8..24, z 8..24, ground 70
    cmds = replay.Replay(Fake(), d).commands(AGE)
    assert cmds[1] == 'title @a title {"text": "Feudal Age"}'
    fw = rockets(cmds)
    assert len(fw) == 3 and cmds[-1].startswith("playsound minecraft:ui.toast.challenge_complete master @a ")
    for c in fw:
        x, y, z = map(float, c.split()[2:5])
        assert 14 <= x <= 18 and 14 <= z <= 18 and y == 72
        assert f"[I; {0x253192}]" in c and '"has_trail": true' in c       # blue (DyeColor firework color)


def test_age_up_of_a_player_in_orange_uses_its_own_town_center():
    d = data([])
    d["objects"] += [TC, dict(TC, player=2, ref=6, footprint=[40, 40, 56, 56])]
    fw = rockets(replay.Replay(Fake(), d).commands(dict(AGE, player=2)))
    assert len(fw) == 3 and all(f"[I; {0xEB8844}]" in c and float(c.split()[2]) > 40 for c in fw)


def test_a_built_town_center_has_its_top():
    r = replay.Replay(Fake(), data([]))
    r.placed.append((1, "TOWN_CENTER", (8, 24, 8, 24)))
    r.tops[(8, 24, 8, 24)] = 85
    assert all(c.split()[3] == "87" for c in rockets(r.commands(AGE)))


def test_no_town_center_keeps_only_the_title():
    cmds = replay.Replay(Fake(), data([])).commands(AGE)
    assert len(cmds) == 2 and not rockets(cmds)


@pytest.mark.mc
def test_fireworks_work_on_a_server(tiny_world, tmp_path):
    from test_paper import paper_reachable
    if not paper_reachable():
        pytest.skip("Paper is not reachable")
    from game import run
    world = shutil.copytree(tiny_world[0], tmp_path / "W")
    with run.Game(world) as game:
        d = data([])
        d["objects"].append(TC)
        for c in replay.Replay(game, d).commands(AGE):
            out = game.command(c)
            assert not re.search("Unknown|Incorrect|Invalid|Expected|error", out), (c, out)
        game.command("forceload add 0 0 63 63")               # no player: the rocket of an unloaded chunk is gone
        time.sleep(2)
        fw = rockets(replay.Replay(game, d).commands(AGE))[0].replace('"LifeTime": 25', '"LifeTime": 2000')
        game.command("kill @e[type=firework_rocket]")
        assert "Summoned" in game.command(fw)
        path = 'FireworksItem.components."minecraft:fireworks".explosions[0]'
        out = [game.command(f"data get entity @e[type=firework_rocket,limit=1] {path}.{k}") for k in ("shape", "colors")]
        assert '"large_ball"' in out[0] and str(0x253192) in out[1], out    # the server keeps the explosion
