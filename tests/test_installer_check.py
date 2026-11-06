"""The action parser and the console parse of tools/installer_check.py (#5885)."""
import pytest

from tools import installer_check as ic


def test_parse_actions():
    assert ic.parse_actions("key:1;btn:1;shot:select") == [("key", ["1"]), ("btn", ["1"]), ("shot", ["select"])]
    assert ic.parse_actions("look:10,-5; hold:1,2,30,0;slot:3,6;") == [
        ("look", ["10", "-5"]), ("hold", ["1", "2", "30", "0"]), ("slot", ["3", "6"])]
    assert ic.parse_actions("type:hello, world") == [("type", ["hello, world"])]


@pytest.mark.parametrize("bad", ["jump:1", "look:1", "key:", "hold:1,2"])
def test_parse_actions_bad(bad):
    with pytest.raises(ValueError):
        ic.parse_actions(bad)


def test_console_parse():
    text = ("Starting...\nJoin the server localhost:25601 (Minecraft 26.3, multiplayer, direct connection).\n"
            "Saved the game: aoe2mc-game OUTWorld --play --load save1\n")
    assert ic.find_port(text) == 25601
    assert ic.find_saved(text) == "aoe2mc-game OUTWorld --play --load save1"
    assert ic.find_port("no server") is None and ic.find_saved("stopped") is None
