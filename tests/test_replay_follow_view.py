"""Live replay --follow: the spectators follow the rider of a mounted unit, not the horse (#1095), over its shoulder
(#1660)."""
import json
import os
import re
import shutil
import sys
import time

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "game"))
import replay  # noqa: E402
from test_replay import Fake, data  # noqa: E402
from test_replay_follow import move  # noqa: E402

HORSE = "00000000-0000-0000-0000-000000001095"
RIDER = "00000000-0000-0000-0000-000000002095"
IDS = ("[I;0,0,0,4245]", "[I;0,0,0,8341]")                           # the int arrays of HORSE and RIDER


def follow(uuid):
    r = replay.Replay(Fake(), data([]), follow=1)
    r.grid()
    r.units[7] = r.gather.Villager(uuid, (20.0, 100.0, 20.0))
    return r.spectate(move(0, 1, 7))


def test_the_rider_takes_the_tag_and_the_spectators_look_through_it():
    tag = replay.FOLLOWED
    assert follow("u1") == [f"tag @e[tag={tag}] remove {tag}", f"tag u1 add {tag}",
                            f"execute as u1 on passengers run tag u1 remove {tag}",     # a rider: not the horse
                            f"execute as u1 on passengers run tag @s add {tag}"]       # Paper: Follow.java


def pos(game, who):
    return [float(v) for v in re.findall(r"(-?[\d.]+)d", game.command(f"data get entity {who} Pos"))]


@pytest.mark.mc
def test_a_spectator_on_a_server_follows_the_rider(tiny_world, tmp_path):
    import mc_shot
    from test_mc_check import mojang_reachable
    from test_paper import paper_reachable
    if not all(shutil.which(t) for t in ("Xvfb", "import", "xdotool")) or not mojang_reachable() \
            or not paper_reachable():
        pytest.skip("Xvfb, xdotool, Mojang or Paper is not available")
    from game import run
    world = shutil.copytree(tiny_world[0], tmp_path / "W")
    d = json.load(open(world / "aoe2mc.json"))
    with run.Game(world) as game, mc_shot.Client(game.game_port, game.version) as client:
        client.wait_join(lambda: "aoe2mc" in game.command("list").split(":", 1)[-1])
        game.command("gamemode spectator aoe2mc")
        game.command("tp aoe2mc 0 120 0")
        assert "Summoned" in game.command(f"summon horse 20.5 100 20.5 {{UUID:{IDS[0]},NoAI:1b,Tame:1b,"
                                          f"Passengers:[{{id:\"minecraft:zombie\",UUID:{IDS[1]},NoAI:1b}}]}}")
        r = replay.Replay(game, dict(d, timeline=[]), follow=1)
        r.grid()
        r.units[7] = r.gather.Villager(HORSE, (20.0, 100.0, 20.0))
        out = [game.command(c) for c in r.spectate(move(0, 1, 7))]
        time.sleep(2)
        assert "Added tag" in out[-1], out
        cam, horse, rider = pos(game, "aoe2mc"), pos(game, HORSE), pos(game, RIDER)
        assert len(cam) == 3 and rider[1] - horse[1] > 0.1, (out, cam, horse, rider)
        assert cam[1] - rider[1] > 1.5 and abs(cam[2] - (rider[2] - 4)) < 0.3, (cam, rider)   # behind the rider (#1660)
        assert f"{replay.FOLLOWED}" not in game.command(f"data get entity {HORSE} Tags")
