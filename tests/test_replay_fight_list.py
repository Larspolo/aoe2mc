"""The list of the large fights in the live replay (#2949): chat lines at the start and a page of the chest menu."""
import json
import os
import sys
from urllib.parse import unquote

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lang  # noqa: E402
import replay  # noqa: E402
import replay_input as ri  # noqa: E402
from test_replay import Fake, data  # noqa: E402
from test_replay_input import Scores, poll  # noqa: E402

PLAYERS = {1: ("Player 1 (Britons)", "blue"), 2: ("Player 2 (Aztecs)", "gold")}
FIGHTS = [{"start": 754000, "end": 790000, "players": [1, 2], "tile": [30, 30], "units": 24},
          {"start": 65000, "end": 70000, "players": [1, 2], "tile": [9, 9], "units": 11}]


def test_the_chat_lines_name_time_players_units_and_the_trigger():
    lines = ri.fight_lines(FIGHTS, PLAYERS)
    assert len(lines) == 3 and "Large fights" in lines[0]
    got = [json.loads(c[len("tellraw @a "):]) for c in lines[1:]]
    for i, (line, time, units) in enumerate(zip(got, ("12:34", "01:05"), (24, 11))):
        assert line["click_event"] == {"action": "run_command", "command": f"/trigger aoe_replay set {ri.FIGHT + i}"}
        assert line["extra"][0]["text"] == f"[{time}] "
        assert {"text": "Player 1 (Britons)", "color": "blue"} in line["extra"]
        assert {"text": "Player 2 (Aztecs)", "color": "gold"} in line["extra"]
        assert lang.plain(line["extra"][-1]) == f" ({units} units)"
    assert ri.FIGHT > ri.FIGHTS > ri.VIEW


def test_the_fight_page_of_the_menu():
    game = Scores()
    control = {"speed": 1.0, "paused": False, "time": 0, "view": None, "players": PLAYERS, "fights": FIGHTS}
    game.click("ben", ri.MENU)
    inp = poll(game, control)
    menus = [c for c in game.sent if c.startswith("aoe menu ben Replay ")]
    assert len(menus) == 1 and "17:iron_sword:Fights" in menus[0]
    inp.open_fights("ben")
    pages = [unquote(c) for c in game.sent if c.startswith("aoe menu ben Fights ")]
    assert len(pages) == 1
    assert "0:iron_sword:12:34 Player 1 (Britons) vs Player 2 (Aztecs)" in pages[0]
    assert "1:iron_sword:01:05 Player 1 (Britons) vs Player 2 (Aztecs)" in pages[0]
    game.menus["ben"]("ben", 1, False)
    assert f"scoreboard players set ben aoe_replay {ri.FIGHT + 1}" in game.sent


def test_no_fight_gives_no_list_and_no_menu_item():
    assert ri.fight_lines([], PLAYERS) == []
    game = Fake()
    replay.Replay(game, data([])).run(clock=lambda: 0.0, sleep=lambda s: None, log=None, bar=True)
    assert not any("Large fights" in c or "aoe_replay set" in c for c in game.sent)
