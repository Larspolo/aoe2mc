"""Live replay with --camera player: the info line reads the eye of the camera entity, not of the player (#5413).
A spectator that looks through an entity (/spectate) keeps its own Pos and Rotation. Fake RCON."""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "game"))
import lang  # noqa: E402
import replay  # noqa: E402
from test_replay_inspect import UUID, bars, setup  # noqa: E402

CAM = f"@e[type=item_display,tag={replay.CAMERA_ENTITY},limit=1]"


def answer(cmd):
    """Steve stays far away and looks down; the camera entity is at (26, 71.62, 40) and looks north (-z)."""
    if cmd.endswith("Health"):
        return f"{UUID} has the following entity data: 20.5f"
    if cmd == "data get entity Steve playerGameType":
        return "Steve has the following entity data: 3"
    data = {"data get entity Steve Pos": "[189.4d, 186.6d, 290.6d]", "data get entity Steve Rotation": "[-135.0f, 60.0f]",
            f"data get entity {CAM} Pos": "[26.0d, 71.62d, 40.0d]", f"data get entity {CAM} Rotation": "[180.0f, 0.0f]"}
    return f"X has the following entity data: {data[cmd]}" if cmd in data else ""


def test_the_camera_entity_gives_the_line_of_its_unit():
    r = setup()
    r.game.command = lambda cmd: r.game.sent.append(cmd) or answer(cmd)
    r.glide = (20, [26.0, 71.62, 40.0], 0)                      # --camera player: the entity exists
    (c,) = bars(r.inspect(10000, clock=lambda: 0.0))
    assert lang.plain(json.loads(c.split(" actionbar ", 1)[1])[0]).startswith(replay.pretty("ARCHER"))


def test_without_the_camera_entity_the_player_eye_counts():
    r = setup()
    r.game.command = lambda cmd: r.game.sent.append(cmd) or answer(cmd)
    assert not bars(r.inspect(10000, clock=lambda: 0.0))
