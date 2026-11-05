"""The AI functions of an XS script (game/xs_host.py, #5846): goals, signals, AI script goals and strategic numbers of
the AI script (per.Script) of a bot."""
from types import SimpleNamespace as NS

from test_xs_host import side, value

from game import per

SN_ID, SN_NAME = next(iter(per.SN_IDS.items()))


def game():
    g = side()
    bot = NS(g=side(2))
    bot.script = per.Script([], bot)
    g.bots = [bot]
    return g, bot.script


def test_goals():
    g, s = game()
    value(g, "0; xsSetGoal(7, 42)")
    assert s.goals[7] == 42
    assert value(g, "xsGetGoal(7) + xsGetGoal(8)") == 42


def test_strategic_numbers_by_id():
    g, s = game()
    assert value(g, f"xsGetStrategicNumber({SN_ID})") == per.SN[SN_NAME]
    value(g, f"0; xsSetStrategicNumber({SN_ID}, 33)")
    assert s.sn[SN_NAME] == 33 and value(g, f"xsGetStrategicNumber({SN_ID})") == 33


def test_signals_and_ai_script_goals():
    g, s = game()
    s.table("signal")[3] = 1
    assert value(g, "xsGetAiSignal(3) + xsGetAiSignal(4)") == 1
    value(g, "0; xsSetAiScriptGoal(5, true)")
    assert s.table("event")[5] == 1 and value(g, "xsGetAiScriptGoal(5)", "bool") is True


def test_context_player_and_no_script(capsys):
    g, s = game()
    value(g, "0; xsSetContextPlayer(2); xsSetGoal(1, 9)")
    assert s.goals[1] == 9
    assert value(side(), "xsGetGoal(1)") == -1
    assert "AI script of player" in capsys.readouterr().err
