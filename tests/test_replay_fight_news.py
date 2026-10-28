"""The live replay tells the viewers when a large fight starts: a chat line, a horn and a click (#2951)."""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from test_replay import Fake, data  # noqa: E402
from test_replay_fights import battle  # noqa: E402

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "game"))

import mcvalid  # noqa: E402
import replay  # noqa: E402
import replay_input as ri  # noqa: E402

HORN = "playsound minecraft:event.raid.horn master @a ~ ~ ~ 1 1 1"


def timeline(start):
    """Player 1 owns 100 and player 2 owns 200 (a stop each): the battle at `start` is a fight of both players."""
    owners = [{"time": 0, "player": 1, "kind": "move", "objects": [100], "tile": [0, 0]},
              {"time": 0, "player": 2, "kind": "move", "objects": [200], "tile": [0, 0]}]
    return owners + battle(start, [10, 10])


def chat(game):
    return [json.loads(c[len("tellraw @a "):]) for c in game.sent if c.startswith("tellraw @a ") and '"Fight: "' in c]


def test_a_fight_start_sends_the_chat_line_and_the_horn():
    game = Fake()
    replay.Replay(game, data(timeline(60000))).run(clock=lambda: 0.0, sleep=lambda s: None, log=None)
    lines = chat(game)
    assert len(lines) == 1
    line = lines[0]
    assert line["extra"][0] == {"text": "Fight: "}
    assert {"text": "Player 1 (Britons)", "color": "blue"} in line["extra"]
    assert {"text": "Player 2 (Aztecs)", "color": "gold"} in line["extra"]
    assert line["extra"][-1] == {"text": ", 12 units", "color": "gray"}
    assert line["click_event"] == {"action": "run_command", "command": f"/trigger aoe_replay set {ri.PLACE}"}
    assert HORN in game.sent and not mcvalid.sound_error(HORN.split()[1])


def test_a_jump_over_the_fight_start_sends_no_line():
    game = Fake()
    replay.Replay(game, data(timeline(60000))).run(to=120000, clock=lambda: 0.0, sleep=lambda s: None, log=None)
    assert chat(game) == [] and HORN not in game.sent


def test_the_click_puts_the_viewer_above_the_place_without_a_jump():
    control = {"time": 0, "fights": [{"start": 60000, "tile": [10.5, 10.0], "players": [1, 2], "units": 12}]}
    assert ri.apply(ri.PLACE, control) == "Fight place"
    assert control["place"] == [10.5, 10.0] and "jump" not in control
    assert ri.apply(ri.PLACE + 1, control) is None
    assert ri.PLACE == ri.FIGHT + ri.MAX_FIGHTS
