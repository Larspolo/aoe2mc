"""#5376: the chat lines of the game start, the lobby, the ratings, the save and the AI are translate components, with the
English fallback of game/data/texts.jsonl (epic #5343). The player names and the numbers stay arguments."""
import json
import os
import sys
from types import SimpleNamespace

from test_chat_hint import make_game

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "game"))
import bot  # noqa: E402
import lang  # noqa: E402
import lobby  # noqa: E402
import ratings  # noqa: E402
import savegame  # noqa: E402
import table  # noqa: E402

from game import run  # noqa: E402

TEXTS = {r["name"]: r["en_us"] for r in table.load("texts.jsonl")}


def payload(command):
    """The JSON of a tellraw command: "tellraw TARGET JSON" (the target has no space)."""
    return json.loads(command.split(" ", 2)[2])


def check(c, key):
    """The component is a translate of key whose fallback is the English line of the table."""
    assert c["translate"] == key
    assert c["fallback"] == TEXTS[key] == lang.en_us()[key]
    return c


def test_the_game_start_chat_hint_is_a_translate_component():
    g, sent = make_game(2)
    g.side("Alex")
    c = check(payload(sent[1]), run.CHAT_HINT_KEY)
    assert c["color"] == "gray" and c["fallback"] == run.CHAT_HINT


def test_the_lobby_says_the_player_is_translated(monkeypatch):
    sent = []
    g = SimpleNamespace(game=SimpleNamespace(sides={}, choose=lambda p, n: True), command=sent.append,
                        players={}, data={})
    monkeypatch.setattr(lobby, "count", lambda g: 2)
    monkeypatch.setattr(lobby, "name", lambda g, n, me=None: "Player 1")
    monkeypatch.setattr(lobby.menu, "close", lambda g, p: None)
    assert lobby.choose(g, "Alex", 1)
    c = check(payload(sent[0]), "aoe2mc.lobby.you_play")
    assert c["with"] == ["Player 1"] and c["color"] == "gold"


def test_the_rating_change_is_a_translate_component():
    sent = []
    ratings.announce(SimpleNamespace(command=sent.append), [("Steve", 1000, 1016)])
    c = check(payload(sent[0]), "aoe2mc.ratings.change")
    assert c["with"] == ["Steve", "1000", "1016"]


def test_the_save_line_is_a_translate_component(monkeypatch):
    sent = []
    game = SimpleNamespace(command=sent.append, world="w")
    g = SimpleNamespace(game=game, command=sent.append)
    monkeypatch.setattr(savegame, "folder", lambda w: "f")
    monkeypatch.setattr(savegame, "write", lambda f, w, d: "f/save-1.json")
    monkeypatch.setattr(savegame, "dump", lambda x: {})
    savegame.save(g, "Alex")
    c = check(payload(sent[-1]), "aoe2mc.savegame.saved")
    assert c["with"] == ["save-1.json"] and c["color"] == "green"


def test_the_ai_chat_line_is_a_translate_component_after_the_player_name():
    g = SimpleNamespace(player=2)
    line = bot.ai_line(g, "aoe2mc.bot.cannot_build", "Castle", who="@a[team=p2]")
    assert line.startswith("tellraw @a[team=p2] ")
    prefix, c = payload(line)
    assert prefix == {"text": "<Player 2> ", "color": "gray"}
    check(c, "aoe2mc.bot.cannot_build")
    assert c["with"] == ["Castle"] and c["color"] == "gray"
