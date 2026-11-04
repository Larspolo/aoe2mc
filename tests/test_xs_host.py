"""The game functions of an XS script (game/xs_host.py, #5623): each one reads or changes the fake side."""
import re
from types import SimpleNamespace as NS

import aoe2mc
from game import xs_host
from game.xs_run import Xs

ARCHER = next(i for i, (_, n) in aoe2mc.object_kinds().items() if n == "ARCHER")


def side(player=1):
    g = NS(player=player, stock={"food": 200, "wood": 150, "stone": 0, "gold": 100}, units=[], soldiers={}, sites=[],
           queues={}, techs={"LOOM", "WHEELBARROW"}, bots=[], data={"objects": [], "players": {"1": {"civ": "BRITONS"}}},
           shown=0, scores={}, commands=[], t0=0.0, clock=lambda: 30.0)

    def command(cmd):
        g.commands.append(cmd)
        if m := re.fullmatch(r"scoreboard players set (\S+) aoe_var (-?\d+)", cmd):
            g.scores[m[1]] = int(m[2])
        if m := re.fullmatch(r"scoreboard players get (\S+) aoe_var", cmd):
            return f"{m[1]} has {g.scores[m[1]]} [aoe_var]" if m[1] in g.scores else "Can't get value"
        return ""
    g.command = command
    g.show_stock = lambda: setattr(g, "shown", g.shown + 1)
    return g


def value(g, expr, typ="int"):
    x = Xs(f"{typ} r = 0; void main() {{ r = {expr}; }}", out=print, host=xs_host.host(g))
    x.tick(0)
    return x.get("r")


def test_game_time():
    assert value(side(), "xsGetGameTime()") > 0


def test_player_attribute_reads_and_sets_the_stock():
    g = side()
    assert value(g, "xsPlayerAttribute(1, 3)", "float") == 100
    value(g, "0; xsSetPlayerAttribute(1, 1, 75)")
    assert g.stock["wood"] == 75 and g.shown == 1


def test_object_counts():
    g = side()
    g.soldiers = {"a": "ARCHER", "b": "ARCHER", "c": "MILITIA"}
    g.queues = {(0, 0): [{"name": "ARCHER"}]}
    assert value(g, f"xsGetObjectCount(1, {ARCHER})") == 2
    assert value(g, f"xsGetObjectCountTotal(1, {ARCHER})") == 3


def test_trigger_variables():
    g = side()
    value(g, "0; xsSetTriggerVariable(4, 9)")
    assert g.scores == {"#v4": 9}
    assert value(g, "xsTriggerVariable(4) + xsTriggerVariable(5)") == 9


def test_civilization_and_techs():
    g = side()
    assert value(g, "xsGetPlayerCivilization(1)") == xs_host.civ_id("BRITONS") > 0
    assert value(g, "xsGetPlayerNumberOfTechs(1)") == 2


def test_a_bot_side():
    g = side()
    g.bots = [NS(g=side(player=2))]
    assert value(g, "xsGetPlayerNumberOfTechs(2)") == 2


def test_unknown_player_or_attribute_warns_once_and_the_script_goes_on(capsys):
    g = side()
    assert value(g, "xsPlayerAttribute(1, 99) + xsPlayerAttribute(1, 99) + xsGetObjectCount(7, 4) + 5") == 5
    assert capsys.readouterr().err.splitlines() == ["XS script: unknown attribute 99: skipped",
                                                    "XS script: unknown player 7: skipped"]
