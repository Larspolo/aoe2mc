"""Jump back to an earlier game time in a running replay (#979), with a fake clock and a fake RCON: run stops,
the world goes back to its start, and a fresh replay jumps forward to the time."""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import replay  # noqa: E402
import replay_input as ri  # noqa: E402
from test_replay import data  # noqa: E402
from test_replay_control import Clock  # noqa: E402
from test_replay_jump import MIL, timeline  # noqa: E402
from test_replay_walk import HOUSE, VIL  # noqa: E402


def world():
    d = data(timeline() + [{"time": 660000, "player": 1, "kind": "chat", "text": "t660000"}])
    d["objects"] += [VIL, MIL, HOUSE]
    return d


def state(r):
    """What the world shows: the buildings, the units and their places, the deleted objects."""
    return (sorted(map(str, r.placed)), sorted((i, v.name, v.cell, v.pos) for i, v in r.units.items()),
            sorted(r.moving), r.pop, r.ages)


def rewind(back_at=300, to=300000.0, paused=False, speed=2.0):
    """Play to game time back_at × speed (s), then jump back to `to` (ms)."""
    game, made, restarts, done = Clock(), [], [], []

    def make():
        made.append(replay.Replay(game, world()))
        return made[-1]

    def poll(control):
        if game.now >= back_at and not done:
            done.append(control["time"])
            control["jump"], control["paused"] = to, paused
        elif done and game.now >= back_at + 50:                         # continue after a pause of 50 s
            control["paused"] = False

    def restart():
        restarts.append(len(game.sent))
    stats = replay.live(make, speed, 0, restart, clock=lambda: game.now, sleep=game.sleep, log=None, poll=poll,
                        bar=True)
    return game, made, restarts, done, stats


def fresh(to=300000.0, paused=False, speed=2.0):
    game = Clock()
    r = replay.Replay(game, world())
    r.run(speed, 0, clock=lambda: game.now, sleep=game.sleep, log=None, to=to, paused=paused, bar=True,
          poll=lambda c: c.update(paused=False) if game.now >= 50 else None)
    return game, r


def test_a_jump_back_gives_the_state_of_a_fresh_replay_with_a_jump():
    game, made, restarts, done, stats = rewind()                       # at 10:00 (speed 2) back to 5:00
    assert len(made) == 2 and len(restarts) == 1 and stats.get("rewind") is None
    assert "kill u2" in game.sent[:restarts[0]]                         # the delete of 2:30 played before
    ref, r = fresh()
    assert state(made[1]) == state(r)
    after = game.sent[restarts[0]:]
    assert after == ref.sent                                           # the same commands as a fresh jump to 5:00


def test_a_jump_back_shows_a_loading_text_and_keeps_the_speed_and_the_pause():
    game, made, restarts, _, _ = rewind(paused=True)
    before = game.sent[:restarts[0]]
    assert any("Jump to 05:00 ..." in c for c in before[-4:]) and "join it again" in before[-1]
    assert made[1].speed == 2.0
    ref, _ = fresh(paused=True)
    assert game.sent[restarts[0]:] == ref.sent


def test_a_jump_back_without_restart_changes_nothing():
    game = Clock()
    stats = replay.live(lambda: replay.Replay(game, world()), 1.0, 0, None, clock=lambda: game.now, sleep=game.sleep,
                        log=None, poll=lambda c: c.update(jump=1000.0) if game.now > 200 and not c.get("x") and
                        c.update(x=1) is None else None)
    assert stats.get("rewind") is None and "t400000" in game.at


def test_the_input_jumps_back_1_and_5_minutes_not_before_0():
    control = {"time": 400000.0}
    assert ri.apply(ri.BACK, control) == "Back to 05:40" and control["jump"] == 340000.0
    control = {"time": 200000.0}
    assert ri.apply(ri.BACK5, control) == "Back to 00:00" and control["jump"] == 0
    assert {ri.BACK, ri.BACK5} <= set(ri.actions())


@pytest.mark.mc
def test_a_restart_puts_the_world_back_on_the_same_port(tiny_world, tmp_path):
    """run.py: save the start world, change it, stop the server, restore the world, start again (#979)."""
    import shutil

    from test_paper import paper_reachable
    if not paper_reachable():
        pytest.skip("Paper is not available")
    from game import run
    world = shutil.copytree(tiny_world[0], tmp_path / "W")
    with run.Game(world) as game:
        game.forceload()
        game.command("setblock 2 100 2 minecraft:diamond_block")
        saved, port = run.save(game), game.game_port
        try:
            game.command("setblock 2 100 2 minecraft:gold_block")
            game.command("summon minecraft:pig 2 101 2 {Tags:[\"rewind\"],NoAI:1b}")
            assert "Test passed" in game.command("execute if block 2 100 2 minecraft:gold_block")
            game.stop()
            run.restore(saved, game.world)
            game.start()
            game.forceload()
            assert game.game_port == port
            assert "Test passed" in game.command("execute if block 2 100 2 minecraft:diamond_block")
            assert "Test failed" in game.command("execute if entity @e[tag=rewind]")
        finally:
            shutil.rmtree(saved, ignore_errors=True)
