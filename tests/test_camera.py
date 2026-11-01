"""The camera mode of the game program (game/camera.py, Camera.java): the hotbar item switches the floor and the
speed of its player, a shift click selects the next speed, and a click picks targets farther than 64 blocks."""
import json
import math
import re
import shutil
import time
import types

import pytest
from test_gather import FakeServer, grid

from game import camera, fleet, gather


class Server(FakeServer):
    """FakeServer with the camera item in the hand of Steve and the answer of `aoe camera Steve`."""

    def __init__(self):
        super().__init__({})
        self.on = False

    def command(self, cmd):
        out = super().command(cmd)
        if cmd.startswith("execute if items entity Steve weapon.mainhand") and "aoe_camera:1b" in cmd:
            return "Test passed"
        if cmd == "aoe camera Steve":
            return f"Camera: {'on' if self.on else 'off'}"
        if cmd.startswith("aoe camera Steve "):
            self.on = cmd.split()[3] == "on"
        return out


def game(rows=None):
    s = Server()
    rows = rows or [[64] * 16 for _ in range(16)]
    return s, types.SimpleNamespace(command=s.command, map=gather.Map(grid(rows)), paper=True, who="@a")


def turned(server, word):
    return [c for c in server.log if c.startswith(f"aoe camera Steve {word}")]


def test_the_floor_is_above_the_highest_ground_over_the_whole_map():
    rows = [[64] * 16 for _ in range(16)]
    rows[3][5], rows[4][4] = 70, "-"                                   # a hill and water
    _, g = game(rows)
    assert camera.floor(g) == (70 + camera.UP, 0, 0, 15, 15)


def test_a_click_turns_the_mode_on_and_a_second_click_off():
    server, g = game()
    assert camera.click(g, "Steve") is True
    y, x0, z0, x1, z1 = camera.floor(g)
    assert turned(server, "on") == [f"aoe camera Steve on {y} {x0} {z0} {x1} {z1} {camera.SPEEDS[camera.START]}"]
    assert camera.click(g, "Steve") is False
    assert turned(server, "off") == ["aoe camera Steve off"] and len(turned(server, "on")) == 1


def test_a_shift_click_selects_the_next_speed_and_wraps():
    server, g = game()
    n = len(camera.SPEEDS)
    camera.click(g, "Steve", shift=True)                               # off: no floor, the next on has the speed
    assert not turned(server, "on") and not server.on
    camera.click(g, "Steve")
    assert turned(server, "on")[-1].endswith(f" {camera.SPEEDS[(camera.START + 1) % n]}")
    for k in range(2, n + 2):                                          # on: each shift click sends the new speed
        camera.click(g, "Steve", shift=True)
        assert turned(server, "on")[-1].endswith(f" {camera.SPEEDS[(camera.START + k) % n]}") and server.on
    assert not turned(server, "off")


def test_the_view_hint_comes_once_and_only_for_a_wider_view(monkeypatch):
    server, g = game()
    monkeypatch.setattr(camera, "SPEEDS", (camera.PLAIN, camera.PLAIN + 1))
    monkeypatch.setattr(camera, "START", 0)
    hints = lambda: [c for c in server.log if c.startswith("tellraw Steve") and "aoe2mc.camera.fov" in c]   # noqa: E731
    camera.click(g, "Steve")
    assert not hints()
    for _ in range(3):
        camera.click(g, "Steve", shift=True)
    assert len(hints()) == 1


def test_the_item_comes_only_on_paper():
    server, g = game()
    camera.give(g)
    assert any(f"hotbar.{camera.SLOT} with {camera.ITEM}" in c for c in server.log)
    assert camera.SLOT not in [s for s, _ in gather.GROUPS.values()] + [gather.goto.SLOT, gather.diplomacy.SLOT]
    server.log.clear()
    g.paper = False
    camera.give(g)
    assert not server.log


def test_a_stick_use_with_the_item_switches_the_mode_and_is_no_click():
    server = Server()
    g = gather.Gather(server, grid([[64] * 16 for _ in range(16)])).setup()
    g.paper = True
    server.scores["aoe_use"] = 1
    assert "Steve" not in g.clicks()
    assert server.on and turned(server, "on")


@pytest.mark.parametrize("far", [100, gather.REACH - 2, gather.REACH + 8])
def test_a_click_picks_the_ground_and_a_unit_up_to_the_reach(far):
    """far: the length of the ray from the eye on a camera floor 30 blocks up to the ground, to the south-east."""
    up = 30 + 1.62
    n = math.ceil(far / math.sqrt(2)) + 4
    m, eye = gather.Map(grid([[64] * n for _ in range(n)])), (1.5, 64 + up, 1.5)
    d = gather.direction(-45, math.degrees(math.asin(up / far)))
    hit = (math.floor(far * 4) + 1) / 4                                # the first step of 1/4 block in the ground
    x, z = (math.floor(eye[i] + d[i] * hit) for i in (0, 2))
    t = (up - 1) / -d[1]                                               # the ray at the height of a unit center
    unit = {"u": (eye[0] + d[0] * t, 64.0, eye[2] + d[2] * t)}
    near = far <= gather.REACH
    assert m.pick_ground(eye, d) == ((x, z) if near else None)
    assert fleet.pick(types.SimpleNamespace(map=m), eye, d) == ((x, z) if near else None)
    assert gather.pick_unit(eye, d, unit) == ("u" if near else None)


@pytest.mark.mc
def test_the_floor_holds_the_player_in_the_real_client(tiny_world, tmp_path):
    """The 26.3 server sends the real blocks under a player that stands where it has no block (once in 200 ticks,
    forceSendPlayerSupportBlocks): the player stays on the floor (Camera.onMove), and off brings the normal values."""
    import mc_shot
    from test_mc_check import mojang_reachable
    from test_paper import paper_reachable
    if not all(shutil.which(t) for t in ("Xvfb", "import")) or not mojang_reachable() or not paper_reachable():
        pytest.skip("Xvfb, Mojang or Paper is not available")
    from game import run
    world = shutil.copytree(tiny_world[0], tmp_path / "W")
    y, x0, z0, x1, z1 = camera.floor(types.SimpleNamespace(map=gather.Map(json.load(open(world / "aoe2mc.json")))))
    with run.Game(world) as game, mc_shot.Client(game.game_port, game.version) as client:
        client.wait_join(lambda: "aoe2mc" in game.command("list").split(":", 1)[-1])
        client.wait_loaded(game)
        feet = lambda: float(re.findall(r"(-?[\d.]+)d", game.command("data get entity aoe2mc Pos"))[1])   # noqa: E731
        reach = lambda: game.command("attribute aoe2mc minecraft:block_interaction_range get").split()[-1]   # noqa: E731
        game.command(f"tp aoe2mc {(x0 + x1) // 2 + 0.5} {y + 5} {(z0 + z1) // 2 + 0.5} 180 40")
        assert game.command(f"aoe camera aoe2mc on {y} {x0} {z0} {x1} {z1} 5").startswith("Camera on: 1 players")
        heights = []
        for _ in range(24):                                            # 12 s: more than 200 ticks
            time.sleep(0.5)
            heights.append(feet())
        assert min(heights) == max(heights) == y + 1 and float(reach()) == 0
        assert game.command("aoe camera aoe2mc off").startswith("Camera off: 1 players")
        assert feet() < y + 1 and float(reach()) > 0
