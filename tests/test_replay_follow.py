"""Live replay: --follow N, the spectators look through the units of player N (#738). Fake RCON."""
import os
import re
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "game"))
import replay  # noqa: E402
from test_replay import Fake, data  # noqa: E402
from test_replay_walk import VIL  # noqa: E402

VIL2 = dict(VIL, uuid="u3", ref=8, tile=[4.5, 10.5])
ENEMY = dict(VIL, uuid="u2", ref=11, player=2, tile=[12.5, 10.5])


def move(t, player, i, tile=(8.5, 8.5)):
    return dict(time=t, player=player, kind="move", objects=[i], tile=list(tile))


def play(timeline, follow):
    d = data(timeline)
    d["objects"] += [VIL, VIL2, ENEMY]
    now, game = [0.0], Fake()

    def sleep(s):
        now[0] += s
    replay.Replay(game, d, follow=follow).run(clock=lambda: now[0], sleep=sleep, log=None, finish=True)
    return [c.split()[1] for c in game.sent if c == f"tag {c.split()[1]} add {replay.FOLLOWED}"]


def test_follow_names_only_units_of_the_player_at_most_once_per_15_seconds():
    tl = [move(0, 1, 7), move(1000, 2, 11), move(5000, 1, 8), move(1000 + replay.FOLLOW_MS, 1, 8)]
    assert play(tl, 1) == ["u1", "u3"]                    # 5 s: too early; 16 s: the next unit
    assert play(tl, 2) == ["u2"]


def test_the_command_goes_to_each_spectator():
    r = replay.Replay(Fake(), data([]), follow=1)
    r.grid()
    r.units[7] = r.gather.Villager("u1", (0.0, 70.0, 0.0))
    assert r.spectate(move(0, 1, 7))[-1] == f"execute as @a[gamemode=spectator] run spectate @e[tag={replay.FOLLOWED},limit=1] @s"


def test_a_deleted_unit_gives_the_camera_to_the_next_event():
    tl = [move(0, 1, 7), dict(time=1000, player=1, kind="delete", objects=[7]), move(2000, 1, 8)]
    assert play(tl, 1) == ["u1", "u3"]


def test_without_follow_no_spectate():
    assert play([move(0, 1, 7), move(20000, 1, 8)], None) == []


@pytest.mark.mc
def test_a_spectator_on_a_server_looks_through_the_followed_unit(tiny_world, tmp_path):
    import json
    import shutil
    import time

    import mc_shot
    from test_mc_check import mojang_reachable
    from test_paper import paper_reachable
    if not all(shutil.which(t) for t in ("Xvfb", "import", "xdotool")) or not mojang_reachable() \
            or not paper_reachable():
        pytest.skip("Xvfb, xdotool, Mojang or Paper is not available")
    from game import run
    world = shutil.copytree(tiny_world[0], tmp_path / "W")
    d = json.load(open(world / "aoe2mc.json"))
    uuid = "00000000-0000-0000-0000-000000000738"
    with run.Game(world) as game, mc_shot.Client(game.game_port, game.version) as client:
        client.wait_join(lambda: "aoe2mc" in game.command("list").split(":", 1)[-1])
        game.command("gamemode spectator aoe2mc")
        game.command("tp aoe2mc 0 120 0")
        assert "Summoned" in game.command("summon villager 20.5 100 20.5 {UUID:[I;0,0,0,1848],NoAI:1b,NoGravity:1b}")
        r = replay.Replay(game, dict(d, timeline=[]), follow=1)
        r.grid()
        r.units[7] = r.gather.Villager(uuid, (20.0, 100.0, 20.0))
        out = [game.command(c) for c in r.spectate(move(0, 1, 7))]
        time.sleep(2)
        pos = game.command("data get entity aoe2mc Pos")
        assert out and "error" not in out[0].lower(), out
        xyz = [float(v) for v in re.findall(r"(-?[\d.]+)d", pos)]
        assert len(xyz) == 3 and abs(xyz[0] - 20.5) + abs(xyz[2] - 20.5) < 0.5, (out, pos)   # the camera is the unit
