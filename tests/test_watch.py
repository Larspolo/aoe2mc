"""The guided replay check (game/watch.py, #1123) with a fake game and a fake clock."""
import os
import sys
from types import SimpleNamespace

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "game"))
import replay  # noqa: E402
import watch  # noqa: E402


class Game:
    def __init__(self):
        self.sent, self.online, self.server = [], [], SimpleNamespace(log=[])

    def command(self, cmd):
        self.sent.append(cmd)
        if cmd == "list":
            return f"There are {len(self.online)} of a max of 20 players online: {', '.join(self.online)}"
        if cmd.startswith("data get entity"):
            return "u-1 has the following entity data: [10.5d, 64.0d, 20.5d]"
        return ""


def chop_replay():
    v = SimpleNamespace(uuid="u-1", pos=(10.5, 64.0, 20.5), res="wood", tree=(9, 20), name="VILLAGER_MALE")
    return SimpleNamespace(starts=[(1, 1, "TOWN_CENTER", (40, 44, 20, 24))], working={7: 0}, units={7: v}, new=[],
                           map=None, placed=[], T=4)


def drive(guide, control, game, now, steps, at=None, until=None):
    """Call the guide each step (one real second). at: {step: action} with "join" or a chat line; until: stop when
    until() is true."""
    for k in range(steps):
        if until and until():
            return
        act = (at or {}).get(k)
        if act == "join":
            game.online = ["Lars"]
        elif act:
            game.server.log.append(f"[12:00:00 INFO]: <Lars> {act}")
        control["time"] = now[1]
        guide(control)
        now[0] += 1.0                                         # one real second per step
        if not control.get("paused"):
            now[1] += 1000 * control.get("speed", 1)


def test_the_guide_pauses_teleports_plays_at_speed_1_and_takes_the_answer():
    game, now, lines, answers = Game(), [0.0, 0.0], [], []
    stages = watch.stages('[{"at": "0:30", "where": "chopper", "what": "a chop", "ask": "Good?"}, '
                          '{"at": "20:00", "what": "later", "ask": "And?"}]')
    g = watch.Guide(game, stages, 4.0, answers, clock=lambda: now[0], log=lines.append)
    g.r = chop_replay()
    control = {"speed": 4.0, "paused": False}
    drive(g, control, game, now, 10, until=lambda: control["paused"])
    assert any(ln.startswith("READY 1") for ln in lines)
    assert 30000 - watch.LEAD * 4000 <= now[1] < 30000 - watch.LEAD * 3000   # paused 5 real seconds (20 game s) before
    drive(g, control, game, now, 30, at={0: "join"}, until=lambda: not control["paused"])
    assert g.state == "watch"
    assert any(ln.startswith("JOINED") for ln in lines) and any(ln.startswith("PLACE chopper") for ln in lines)
    tag = game.sent.index(f"tag @a add {replay.VIEWER}")
    tp = next(i for i, c in enumerate(game.sent) if c.startswith("tp Lars "))
    assert tag < tp and "facing entity u-1 eyes" in game.sent[tp]
    assert control["speed"] == 1.0 and not control["paused"]          # the moment plays at speed 1
    drive(g, control, game, now, 60, until=lambda: control["paused"])
    assert lines[-1] == "ASK 1" and now[1] > 30000
    drive(g, control, game, now, 2, at={0: "the chop looks right"})
    assert answers == [{"stage": "1", "player": "Lars", "time": answers[0]["time"], "text": "the chop looks right"}]
    assert control["speed"] == 4.0 and not control["paused"]         # back to the start speed
    drive(g, control, game, now, 1)
    assert control.get("jump") == 1200000 - watch.LEAD * 4000        # 20:00 is far: a jump


def test_more_plays_again_and_the_last_answer_stops():
    game, now, lines, answers = Game(), [0.0, 0.0], [], []
    stages = watch.stages("Watch: 0:20 | chopper | Good?")
    g = watch.Guide(game, stages, 2.0, answers, clock=lambda: now[0], log=lines.append)
    g.r, game.online = chop_replay(), ["Lars"]
    control = {"speed": 2.0, "paused": False}
    drive(g, control, game, now, 90, until=lambda: g.state == "answer")
    assert lines[-1] == "ASK 1"
    drive(g, control, game, now, 1, at={0: "more"})
    assert not control["paused"] and g.state == "watch"
    drive(g, control, game, now, 60, until=lambda: g.state == "answer")
    assert lines.count("ASK 1") == 2
    with pytest.raises(watch.Stop):
        drive(g, control, game, now, 2, at={0: "ok"})
    assert [a["text"] for a in answers] == ["ok"]


def test_a_chat_line_before_the_question_is_not_an_answer():
    game, now, answers = Game(), [0.0, 0.0], []
    g = watch.Guide(game, watch.stages('[{"at": 20000, "ask": "Good?"}]'), 1.0, answers,
                    clock=lambda: now[0], log=lambda s: None)
    game.online = ["Lars"]
    drive(g, {"speed": 1.0}, game, now, 20, at={3: "hello"})
    assert g.state in ("join", "count", "watch") and answers == []


def test_stages_of_a_ticket_and_the_end():
    got = watch.stages("Some text\n- Watch: 3:00 | unit:scout | Does it walk?\nTask: Use the jumps | Clear?\n"
                       "Watch: end | building:TOWN_CENTER | Is the end clear?", end=1234000)
    assert [s["at"] if "at" in s else None for s in got] == [180000, None, 1234000]
    assert got[0]["where"] == "unit:scout" and got[1]["task"] == "Use the jumps" and got[2]["ask"] == "Is the end clear?"


def test_places_of_a_building_a_unit_and_a_tile():
    game = Game()
    g = watch.Guide(game, [], 1.0, [], log=lambda s: None)
    g.r = chop_replay()
    g.r.units[8] = SimpleNamespace(uuid="u-2", pos=(30.0, 64.0, 30.0), name="SCOUT_CAVALRY")
    assert g.target("building:town_center")[:4] == (None, 42.0, None, 22.0)
    assert g.target("unit:scout")[0] == "u-2"
    assert g.target("tile:2,3")[1:4] == (10.0, None, 14.0)
    game.online = ["Lars"]
    g.place({"where": "tile:2,3"})
    assert any(c.startswith("spreadplayers") for c in game.sent)
    assert any("tp @s ~ ~3 ~ facing 10.0 ~ 14.0" in c for c in game.sent)


def test_last_asks_the_end_stage_after_the_replay():
    game, answers = Game(), []
    g = watch.Guide(game, watch.stages('[{"at": 9000, "ask": "End?"}]'), 1.0, answers, log=lambda s: None)
    game.server.log.append("[12:00:00 INFO]: <Lars> old")

    def sleep(s):
        game.server.log.append("[12:00:01 INFO]: <Lars> yes")
    g.last(9000, sleep=sleep)
    assert [a["text"] for a in answers] == ["yes"] and answers[0]["time"] == 9
