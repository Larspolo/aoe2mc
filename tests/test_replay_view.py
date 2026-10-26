"""Live replay: a player starts in adventure mode high above the map and looks down at its center (#737)."""
import math
import os
import re
import shutil
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "game"))
import replay  # noqa: E402
from test_replay import Fake, data  # noqa: E402


def play(timeline, **kw):
    now = [0.0]

    def sleep(s):
        now[0] += s
    game = Fake()
    replay.Replay(game, data(timeline, y=70)).run(speed=4, clock=lambda: now[0], sleep=sleep, log=None, **kw)
    return game.sent


def chat(t):
    return {"time": t, "player": 1, "kind": "chat", "text": "hi"}


def test_the_start_puts_each_player_above_the_map_in_adventure_mode():
    sent = play([chat(0), chat(3000)], bar=True)
    start = sent[:sent.index("tag @a add aoe_viewer") + 1]
    assert "gamemode adventure @a" in start
    assert "effect give @a minecraft:slow_falling 60 0 true" in start      # no fall damage before the flight of #910
    assert any(c.startswith("tellraw @a") and "Double-tap Shift: spectator view" in c for c in start)
    tp = next(c for c in start if c.startswith("tp @a "))
    x, y, z, fx, fy, fz = map(float, re.match(r"tp @a (\S+) (\S+) (\S+) facing (\S+) (\S+) (\S+)$", tp).groups())
    assert (fx, fy, fz) == (32, 70, 32)                                     # the center of the 64 x 64 map
    assert 70 < y <= 319
    pitch = math.degrees(math.atan2(y - fy, math.hypot(x - fx, z - fz)))
    assert abs(pitch - replay.VIEW_PITCH) < 1
    assert x < fx and z > fz                                                # it looks to the north-east (SPAWN_YAW)


def test_a_player_who_joins_later_gets_the_view_once_per_game_second():
    sent = play([chat(0), chat(2500)], bar=True)
    join = [c for c in sent if "@a[tag=!aoe_viewer]" in c]
    assert "execute as @a[tag=!aoe_viewer] run gamemode adventure @s" in join
    assert any(c.startswith("execute as @a[tag=!aoe_viewer] run tp @s ") for c in join)
    tags = sum(c == "tag @a[tag=!aoe_viewer] add aoe_viewer" for c in join)
    assert tags == 2                                        # with the clock: the seconds with an event (0 and 2)
    assert "gamemode spectator" not in " ".join(sent)                      # a viewer keeps its own choice (#910)


def test_without_the_bar_no_view_commands():
    sent = play([chat(0), chat(2000)])
    assert not [c for c in sent if "gamemode" in c or "aoe_viewer" in c or c.startswith("tp @a")]


def test_the_view_stays_below_the_build_limit_on_a_large_map():
    r = replay.Replay(Fake(), data([], n=960, y=315))
    tp = next(c for c in r.overview() if c.startswith("tp @a "))
    assert float(tp.split()[3]) == 319


@pytest.mark.mc
def test_the_view_commands_work_on_a_server(tiny_world, tmp_path):
    from test_paper import paper_reachable
    if not paper_reachable():
        pytest.skip("Paper is not reachable")
    from game import run
    world = shutil.copytree(tiny_world[0], tmp_path / "W")
    with run.Game(world) as game:
        r = replay.Replay(game, data([]))
        out = {c: game.command(c) for c in r.overview() + r.overview(join=True)}
    # no player is on the server: "No player was found" and "No entity was found" are the answers of valid commands
    assert not [(c, o) for c, o in out.items() if "Incorrect" in o or "Unknown" in o or "<--[HERE]" in o], out
