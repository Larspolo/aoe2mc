"""The in-game input of a live replay (#688): hotbar items, the chest menu and /trigger aoe_replay."""
import json
import os
import re
import sys
import urllib.parse

import pytest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from test_replay import Fake, data  # noqa: E402

import replay  # noqa: E402
import replay_input as ri  # noqa: E402


class Scores(Fake):
    """A fake RCON with the scores of the players, the item in the main hand and the menus."""
    def __init__(self, kind="paper"):
        super().__init__()
        self.kind, self.scores, self.hand = kind, {"anna": {}, "ben": {}}, {}

    def at(self, sel):
        m = re.fullmatch(r"@a\[scores=\{(\w+)=(\d+)(\.\.)?\}\]", sel)
        lo, open_ = int(m[2]), m[3]
        return [p for p, s in self.scores.items() if s.get(m[1], 0) >= lo and (open_ or s.get(m[1], 0) == lo)]

    def command(self, cmd):
        super().command(cmd)
        if m := re.fullmatch(r"execute if entity (\S+)", cmd):
            return "Test passed" if self.at(m[1]) else "Test failed"
        if m := re.fullmatch(r"execute as (\S+) if items entity @s weapon.mainhand \S+aoe_replay:(\d+)\}\] "
                             r"run scoreboard players set @s aoe_replay (\d+)", cmd):
            for p in self.at(m[1]):
                if self.hand.get(p) == int(m[2]):
                    self.scores[p]["aoe_replay"] = int(m[3])
        elif m := re.fullmatch(r"scoreboard players set (\S+) (\w+) (-?\d+)", cmd):
            for p in self.scores if m[1] == "@a" else [m[1]]:
                self.scores[p][m[2]] = int(m[3])
        elif m := re.fullmatch(r"scoreboard players get (\S+) (\w+)", cmd):
            v = self.scores[m[1]].get(m[2])
            return f"{m[1]} has {v} [{m[2]}]" if v is not None else f"{m[1]} has no score"
        elif cmd == "list":
            return "There are 2 of a max of 20 players online: anna, ben"
        return ""

    def click(self, player, n, menu=False):
        """A right click with the item of action n, or (menu) the trigger score of a menu click."""
        if menu:
            self.scores[player]["aoe_menu"] = n
        else:
            self.hand[player] = n
            self.scores[player]["aoe_replay_use"] = 1


def poll(game, control, n=1):
    inp = ri.Input(game, clock=lambda: poll.t)
    for _ in range(n):
        poll.t += 1
        inp(control)
    return inp


poll.t = 0.0


def test_each_item_sets_the_control_state():
    game, control = Scores(), {"speed": 1.0, "paused": False, "time": 90000}
    inp = ri.Input(game, clock=lambda: poll.t)
    for n, want in ((ri.PAUSE, {"paused": True}), (ri.PAUSE, {"paused": False}), (ri.NEXT, {"speed": 2.0}),
                    (ri.NEXT, {"speed": 4.0}), (ri.JUMP, {"jump": 150000})):
        game.click("anna", n)
        poll.t += 1
        inp(control)
        assert {k: control[k] for k in want} == want, n
        assert game.scores["anna"]["aoe_replay"] == 0 and game.scores["anna"]["aoe_replay_use"] == 0
    assert game.sent[-2:] == ["scoreboard players set @a aoe_replay 0", "scoreboard players enable @a aoe_replay"]
    assert any(c.startswith("title @a actionbar") and "Jump to 02:30" in c for c in game.sent)


@pytest.mark.parametrize("n, want", [(ri.SPEED, {"speed": 0.5}), (ri.SPEED + 4, {"speed": 8.0}),
                                     (ri.JUMP5, {"jump": 310000}), (ri.JUMP10, {"jump": 610000}),
                                     (ri.PAUSE, {"paused": True})])
def test_each_trigger_command_sets_the_control_state(n, want):
    game, control = Scores("vanilla"), {"speed": 1.0, "paused": False, "time": 10000}
    game.scores["ben"]["aoe_replay"] = n                       # /trigger aoe_replay set n
    poll(game, control)
    assert {k: control[k] for k in want} == want


def test_the_speed_after_the_last_is_the_first():
    control = {"speed": 8.0}
    assert ri.apply(ri.NEXT, control) == "Speed 0.5×" and control["speed"] == 0.5


def test_the_chest_opens_the_menu_and_its_clicks_are_actions():
    game, control = Scores(), {"speed": 1.0, "paused": False, "time": 0}
    game.click("ben", ri.MENU)
    inp = poll(game, control)
    opened = [c for c in game.sent if c.startswith("aoe menu ben Replay ")]
    assert len(opened) == 1 and "ben" in game.menus and "11:feather:Speed%202%C3%97" in opened[0]
    game.scores["ben"]["aoe_menu"] = 12 + 1                     # the slot of "Speed 4×"
    poll.t += 1
    inp(control)
    assert control["speed"] == 4.0 and "ben" in game.menus        # the menu stays open


def test_items_only_once_in_each_join_period_and_no_menu_on_vanilla():
    game = Scores("vanilla")
    poll(game, {"speed": 1.0, "paused": False}, n=3)              # 3 s: one give
    gives = [c for c in game.sent if "item replace" in c]
    assert len(gives) == 3 and not any("hotbar.8" in c for c in gives)
    assert sum(c.startswith("scoreboard players enable @a aoe_replay") for c in game.sent) == 1


def test_polls_closer_than_every_send_nothing():
    game = Scores()
    inp = ri.Input(game, clock=lambda: 5.0)
    inp({"speed": 1.0})
    n = len(game.sent)
    inp({"speed": 1.0})
    assert len(game.sent) == n


def test_help_text_has_a_click_for_each_action():
    cmds = [p["click_event"]["command"] for p in json.loads(ri.help_text())["extra"] if "click_event" in p]
    assert cmds == [f"/trigger aoe_replay set {n}" for n in ri.actions()]
    game = Scores()
    ri.Input(game).give()
    assert max(len(c.encode()) for c in game.sent) <= 1446                # else the server closes RCON


def test_replay_gives_the_game_time_to_poll():
    times = []

    def poll_(control):
        times.append(control["time"])
    clock = [0.0]

    def sleep(s):
        clock[0] += s
    events = [{"time": t, "player": 1, "kind": "chat", "text": "x"} for t in (1000, 3000)]
    replay.Replay(Fake(), data(events)).run(2.0, clock=lambda: clock[0], sleep=sleep, log=None, poll=poll_)
    assert times[0] == 0 and max(times) == pytest.approx(3000) and times == sorted(times)


@pytest.mark.mc
def test_a_right_click_pauses_and_continues_a_replay_on_a_server(tiny_world, tmp_path):
    import shutil
    import threading
    import time

    import mc_shot
    from test_mc_check import mojang_reachable
    from test_paper import paper_reachable
    if not all(shutil.which(t) for t in ("Xvfb", "import", "xdotool")) or not mojang_reachable() \
            or not paper_reachable():
        pytest.skip("Xvfb, xdotool, Mojang or Paper is not available")
    from game import run
    world = shutil.copytree(tiny_world[0], tmp_path / "W")
    with run.Game(world) as game, mc_shot.Client(game.game_port, game.version) as client:
        client.wait_join(lambda: "aoe2mc" in game.command("list").split(":", 1)[-1])
        time.sleep(5)                                                  # the world is drawn
        inp = ri.Input(game)
        inp.setup()
        inp({"speed": 1.0, "paused": False})                           # the items
        assert "minecraft:clock" in game.command(                     # RCON cuts a long answer: ask for the model
            'data get entity aoe2mc Inventory[{Slot:0b}].components."minecraft:item_model"')
        client.key("1")
        at, command = {}, game.command

        def timed(c):
            for one in [urllib.parse.unquote_plus(x) for x in c.split(" ")[2:]] if c.startswith("aoe batch ") else [c]:
                if one.startswith("tellraw @a ["):                     # a chat event, not the view text (#737)
                    at[json.loads(one[len("tellraw @a "):])[-1]["text"]] = time.monotonic() - t0   # (in a batch, #2761)
            return command(c)
        game.command = timed

        def player():                                                  # right clicks with the clock at 2 s and 5 s
            for t in (2, 5):
                time.sleep(t - (time.monotonic() - t0))
                client.xdo("click", "3")
                if t == 2:
                    time.sleep(1.5)
                    client.shot(str(tmp_path / "paused.png"))
        events = [{"time": t, "player": 1, "kind": "chat", "text": f"t{t}"} for t in (1000, 4000, 7000)]
        t0 = time.monotonic()
        th = threading.Thread(target=player)
        th.start()
        replay.Replay(game, data(events)).run(1.0, log=None, bar=True, poll=inp)
        th.join()
        assert at["t1000"] < 2 and at["t4000"] > 6.5 and at["t7000"] - at["t4000"] == pytest.approx(3, abs=0.5), at
        assert (tmp_path / "paused.png").stat().st_size > 10000
