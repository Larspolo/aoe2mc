"""The chat, instruction, timer, sound and view functions of an XS script (game/xs_host.py screen, #5844)."""
import json
from types import SimpleNamespace as NS

import diplomacy  # noqa: E402  (game/ is on the path after xs_host)
import fog  # noqa: E402
from test_xs_host import side

import aoe2mc
from game import xs_host
from game.xs_run import Xs

SOUND_PART, SOUND = aoe2mc.SOUNDS[0]


def screen(now=30.0):
    g = side()
    g.clock = lambda: now
    g.map = NS(T=4, y=lambda x, z: 7)
    g.pos = lambda who: (10.0, 7.0, 22.0)
    g.person, g.who = "alex", "@a"
    return g


def run(g, body, typ="int", init="0"):
    x = Xs(f"{typ} r = {init}; void main() {{ {body} }}", out=print, host=xs_host.host(g))
    x.tick(0)
    return x.get("r")


def test_send_chat_to_all_and_to_one_player():
    g = screen()
    assert run(g, 'r = xsSendChat("<RED>Hello"); xsSendChat("Hi", 2);', "bool", "false")
    assert g.commands == ['tellraw @a {"text": "Hello"}', 'tellraw @a[team=p2] {"text": "Hi"}']


def test_instructions_and_clear():
    g = screen()
    run(g, 'xsDisplayInstructions("Go", 5, -1, -1, -1, false, false, "", 1); xsClearInstructions(-1, 1);')
    assert g.commands == ["title @a[team=p1] times 10 100 20", 'title @a[team=p1] subtitle {"text": "Go"}',
                          'title @a[team=p1] title ""', "title @a[team=p1] clear"]


def test_long_instructions_also_go_to_the_chat():
    g = screen()
    msg = "x" * (aoe2mc.SUBTITLE_CHARS + 1)
    run(g, f'xsDisplayInstructions("{msg}");')
    assert g.commands[-1] == "tellraw @a " + json.dumps({"text": msg})


def test_timer_bar_remaining_time_and_clear():
    g = screen(now=0.0)
    run(g, 'xsDisplayTimer(3, "Left: %d", 2, 1);')                    # 2 minutes
    assert "bossbar set aoe2mc:xs_timer3 max 120" in g.commands
    assert 'bossbar set aoe2mc:xs_timer3 name "Left: 2"' in g.commands
    assert run(g, "r = xsUnsyncGetTimerTimeRemaining(3, 2);", "float", "0.0") == 120
    assert run(g, "r = xsClearTimer(3);", "bool", "false")
    assert g.commands[-1] == "bossbar remove aoe2mc:xs_timer3" and not g.xs_timers


def test_timer_counts_down_and_ends():
    g = screen(now=0.0)
    run(g, 'xsDisplayTimer(0, "%d", 70, 3);')                         # m:ss
    from gather import NORMAL
    g.clock = lambda: 10.0 / NORMAL                                    # 10 game seconds
    xs_host.timers(g)
    assert g.commands[-1] == 'bossbar set aoe2mc:xs_timer0 name "1:00"'
    g.clock = lambda: 80.0 / NORMAL
    xs_host.timers(g)
    assert g.commands[-1] == "bossbar remove aoe2mc:xs_timer0" and not g.xs_timers


def test_play_sound_at_a_tile_and_at_each_player():
    g = screen()
    run(g, f'xsPlaySound("{SOUND_PART}", -1, vector(2, 3, 0)); xsPlaySound("{SOUND_PART}", 2);')
    assert g.commands == [f"playsound minecraft:{SOUND} master @a 8.5 7.0 12.5",
                          f"execute as @a[team=p2] at @s run playsound minecraft:{SOUND} master @s"]


def test_no_sound_name_plays_nothing():
    g = screen()
    assert not run(g, 'r = xsPlaySound("");', "bool", "true")
    assert not g.commands


def test_view_position():
    g = screen()
    run(g, "xsSetViewPosition(1, vector(2, 3, 0));")
    assert g.commands == ["tp @a[team=p1] 8.5 7.0 12.5"]
    assert run(g, "r = xsUnsyncGetViewPosition(1);", "vector", "vector(0, 0, 0)") == (2.5, 5.5, 0.0)
    assert run(g, "r = xsUnsyncGetLocalPlayerId();") == 1


def test_selected_units_and_visibility(monkeypatch):
    g, enemy = screen(), screen()
    enemy.player = 2
    monkeypatch.setattr(xs_host, "objects", lambda _: [(5, g, "u-a", "ARCHER"), (6, enemy, "u-b", "MILITIA"),
                                                        (7, enemy, "u-c", "MILITIA")])
    monkeypatch.setattr(xs_host, "ids", lambda _: {"u-a": 5, "u-b": 6, "u-c": 7})
    monkeypatch.setattr(diplomacy, "stance", lambda x, n: "enemy")
    monkeypatch.setattr(fog, "seen", lambda x: set())
    g.selected = {"u-a"}
    g.fog = {"hidden": ["u-c"]}
    assert run(g, "int a = xsUnsyncGetPlayerSelectedUnitIds(); r = xsArrayGetInt(a, 0) * 10 + xsArrayGetSize(a);") == 51
    assert run(g, "r = xsUnsyncIsUnitVisible(5) && xsUnsyncIsUnitVisible(6) && !xsUnsyncIsUnitVisible(7);",
               "bool", "false")
