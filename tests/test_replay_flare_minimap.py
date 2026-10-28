"""A flare of the live replay on the live minimap (#2405, epic #2401): "aoe minimap flare X Z TEAM TICKS" draws a
blinking cross in the player color at the block of the flare for flare.SECONDS of game time."""
import pytest
from test_replay import Fake, data

import aoe2mc
from game import flare, replay


def test_a_flare_with_the_minimap_on_sends_the_minimap_mark():
    r = replay.Replay(Fake(), data([]), ai=True)
    out = r.commands({"time": 5000, "player": 2, "kind": "flare", "tile": [8.5, 3.25]})
    assert out[-1] == f"aoe minimap flare 34 13 p2 {flare.SECONDS * 20}"
    r.speed = 4.0                                                       # 4 times faster: a quarter of the ticks
    out = r.commands({"time": 6000, "player": 1, "kind": "flare", "tile": [2.0, 2.0]})
    assert out[-1] == f"aoe minimap flare 8 8 p1 {flare.SECONDS * 5}"


def test_no_minimap_mark_without_the_plugin():
    r = replay.Replay(Fake(), data([]))
    out = r.commands({"time": 5000, "player": 2, "kind": "flare", "tile": [8.5, 3.25]})
    assert not any(c.startswith("aoe minimap") for c in out)


@pytest.mark.mc
def test_the_plugin_draws_the_flare_at_the_pixel_of_its_block(tmp_path):
    from test_paper import paper_reachable
    if not paper_reachable():
        pytest.skip("Paper is not reachable")
    from game import run
    world = str(tmp_path / "W")
    aoe2mc.convert(aoe2mc.RANDOM_MAP + "arabia", world)               # 480 x 480 blocks
    with run.Game(world) as game:
        game.forceload()
        game.command("team add p1")
        game.command("team modify p1 color red")
        for b in (4, 240, 479):
            px = game.command(f"aoe minimap pixel {b} {b}").split(": ")[1].strip()
            assert game.command(f"aoe minimap flare {b} {b} p1 200").strip() == f"Minimap flare: {px}"
        assert "outside" in game.command("aoe minimap flare -17 240 p1 200")
