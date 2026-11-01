"""Live replay with --camera player: the info line picks a unit near the view ray of the camera entity (#5437).
A spectator through the camera entity cannot aim, so a unit 2 blocks off the ray still gives its line; the free
view keeps the narrow ray. Fake RCON."""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "game"))
import lang  # noqa: E402
import replay  # noqa: E402
from test_replay_inspect import bars, setup  # noqa: E402

CAM = f"@e[type=item_display,tag={replay.CAMERA_ENTITY},limit=1]"


def answer(cmd):
    """Steve stays far away and looks down; the camera entity is at (26, 71.62, 40) and looks north (-z)."""
    if cmd.endswith("Health"):
        return "X has the following entity data: 20.5f"
    if cmd == "data get entity Steve playerGameType":
        return "Steve has the following entity data: 3"
    data = {"data get entity Steve Pos": "[189.4d, 186.6d, 290.6d]", "data get entity Steve Rotation": "[-135.0f, 60.0f]",
            f"data get entity {CAM} Pos": "[26.0d, 71.62d, 40.0d]", f"data get entity {CAM} Rotation": "[180.0f, 0.0f]"}
    return f"X has the following entity data: {data[cmd]}" if cmd in data else ""


def off_ray(glide):
    """The archer stands 2 blocks east of the view ray of the camera entity (x = 28, the ray at x = 26)."""
    r = setup()
    r.units[7].pos = (28.0, 69.0, 30.0)
    r.game.command = lambda cmd: r.game.sent.append(cmd) or answer(cmd)
    r.glide = glide
    return r


def test_the_camera_entity_picks_a_unit_2_blocks_off_the_ray():
    r = off_ray((20, [26.0, 71.62, 40.0], 0))                   # --camera player: the entity exists
    (c,) = bars(r.inspect(10000, clock=lambda: 0.0))
    assert lang.plain(json.loads(c.split(" actionbar ", 1)[1])[0]).startswith(replay.pretty("ARCHER"))


def test_the_free_view_keeps_the_narrow_ray():
    r = off_ray(None)                                           # no camera entity: the player's own eye
    assert not bars(r.inspect(10000, clock=lambda: 0.0))
