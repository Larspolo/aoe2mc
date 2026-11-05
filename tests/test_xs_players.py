"""The diplomacy, victory and player name functions of an XS script (game/xs_host.py, #5843)."""
import json

from game import xs_host
from tests.test_xs_host import side, value


def players(g):
    g.players = {"1": {"civ": "BRITONS", "color": "blue"}, "2": {"civ": "FRANKS", "color": "red", "neutral": [1]},
                 "3": {"civ": "MAYANS", "color": "green"}}
    g.bots = [type("B", (), {"g": side(player=n)})() for n in (2, 3)]
    return g


def test_get_and_set_diplomacy():
    g = players(side())
    g.players["1"]["team"] = g.players["3"]["team"] = 1
    assert [value(g, f"xsGetDiplomacy({a}, {b})") for a, b in ((1, 3), (2, 1), (1, 2))] == [0, 1, 3]
    assert value(g, "xsSetDiplomacy(1, 2, 0, true)", "bool") is True
    assert {"scoreboard players set #p1.p2 aoe_dip 1", "scoreboard players set #p2.p1 aoe_dip 1",
            "scoreboard players set #any aoe_dip 1"} <= set(g.commands)
    assert value(g, "xsSetDiplomacy(1, 1, 0, false)", "bool") is False
    assert value(g, "xsSetDiplomacy(1, 2, 2, false)", "bool") is False


def test_declare_victory(capsys):
    g = players(side())
    value(g, "0; xsDeclareVictory(2, true)")
    assert g.commands == ["scoreboard players set #p2 aoe_win 1"]
    value(g, "0; xsDeclareVictory(2, false)")
    assert "defeat of player 2" in capsys.readouterr().err and len(g.commands) == 1


def test_civ_names():
    g = players(side())
    assert value(g, f"xsGetCivName({xs_host.civ_id('BRITONS')}, false)", "string") == "Britons"
    assert value(g, "xsGetPlayerCivName(2, false)", "string") == "Franks"
    assert value(g, "xsSetPlayerCivName(2, \"Gauls\")", "bool") is True
    assert value(g, "xsGetPlayerCivName(2, false)", "string") == "Gauls"


def test_player_name_and_color():
    g = players(side())
    assert value(g, "xsSetPlayerName(1, \"Arthur\")", "bool") is True
    assert g.players["1"]["name"] == "Arthur"
    assert g.commands[-1] == "team modify p1 displayName " + json.dumps("Arthur")
    assert value(g, "xsGetPlayerColorTag(1)", "string") == "<BLUE>"
    assert value(g, "xsSetPlayerColor(1, 4)", "bool") is True
    assert value(g, "xsGetPlayerColorTag(1)", "string") == "<YELLOW>"
    assert g.commands[-1] == "team modify p1 color yellow"
    assert value(g, "xsSetPlayerColor(1, 99)", "bool") is False


def test_victory_settings_and_timers():
    g = players(side())
    g.data["victory"] = {"condition": "time-limit", "years": 300, "modes": ["regicide", "king-of-the-hill"]}
    g.victory = "time-limit"
    g.wonders = {"w": {"left": 99.5, "player": 2}}
    g.peers, g.hill = [], {"owner": 3, "left": 40.0}
    assert value(g, "xsGetVictoryCondition()") == 3
    assert value(g, "xsGetVictoryConditionForSecondaryGameMode()") == 12
    assert value(g, "xsGetVictoryType()") == 2
    assert value(g, "xsGetVictoryTime() * 10 + xsGetVictoryPlayer()") == 1002
    assert value(g, "xsGetVictoryTimeForSecondaryGameMode() * 10 + xsGetVictoryPlayerForSecondaryGameMode()") == 403
