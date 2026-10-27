"""The chat guide of an owner play test (game/play_guide.py, #1674) on a fake server, and the play-test map
`tools/scenarios.py owner_loop`."""
import contextlib
import io
import math
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "game"))
import combat  # noqa: E402
import play_guide  # noqa: E402
import scenarios  # noqa: E402
from AoE2ScenarioParser.datasets.buildings import BuildingInfo  # noqa: E402
from AoE2ScenarioParser.datasets.units import UnitInfo  # noqa: E402
from AoE2ScenarioParser.scenarios.aoe2_de_scenario import AoE2DEScenario  # noqa: E402


def chat(name, text):
    return f"[12:00:00 INFO]: [Not Secure] <{name}> {text}"


class Server:
    """A fake server: `list` gives the players, the log gets the chat lines of `script` at their seconds."""

    def __init__(self, log, script):
        self.log, self.script, self.now, self.sent, self.online = log, sorted(script), 0.0, [], []
        log.write_text("[11:59:00 INFO]: Done (3.0s)!\n")

    def command(self, cmd):
        self.sent.append(cmd)
        if cmd == "list":
            return f"There are {len(self.online)} of a max of 20 players online: {', '.join(self.online)}"
        return "ok"

    def clock(self):
        return self.now

    def sleep(self, s):
        self.now += s
        while self.script and self.script[0][0] <= self.now:
            _, line = self.script.pop(0)
            if line == "join":
                self.online = ["Lars"]
            else:
                with open(self.log, "a") as f:
                    f.write(line + "\n")


STEPS = [{"name": "1204-arrows", "setup": ["data merge entity {BARRACKS} {Health:10f}", "kill {MILITIA2}", "say {NOPE}"],
          "task": "Garrison 3 villagers.", "ask": "Do the arrows look right?"},
         {"name": "1138-victory", "task": "Type torpedo2.", "ask": "Is the title clear?"}]


def guide(tmp_path, script, steps=STEPS, values=None):
    s = Server(tmp_path / "latest.log", script)
    lines = []
    g = play_guide.Guide(s.command, str(tmp_path / "latest.log"), steps, values or {"{BARRACKS}": "b-1", "{MILITIA2}": "m-2"},
                         clock=s.clock, sleep=s.sleep, say_log=lambda *a: lines.append(" ".join(map(str, a))))
    return g, s, lines


def test_the_guide_runs_each_step_and_takes_the_answers(tmp_path):
    g, s, lines = guide(tmp_path, [(5, "join"), (6, chat("Lars", "early words")), (30, chat("Lars", "ok")),
                                   (60, chat("Lars", "It worked, but the units")), (65, chat("Lars", "stood still."))])
    snapshots = [list(a) for a in g.run()]
    assert [a["text"] for a in g.answers] == ["ok", "It worked, but the units stood still."]   # two lines: one answer
    assert len(snapshots) == 2 and snapshots[0] == g.answers[:1]          # the file is written after each answer
    assert lines[0] == "JOINED ['Lars']" and lines[-1] == "DONE 2 answers"
    assert [ln.split(":")[0] for ln in lines if ln.startswith(("ASK", "ANSWER"))] == \
        ["ASK 1204-arrows", "ANSWER 1204-arrows", "ASK 1138-victory", "ANSWER 1138-victory"]
    assert "data merge entity b-1 {Health:10f}" in s.sent and "kill m-2" in s.sent
    assert "say {NOPE}" in s.sent                                         # an unknown name stays: the server says so
    asks = [c for c in s.sent if c.startswith("tellraw")]
    assert "Step 1 of 2: Garrison 3 villagers." in asks[0] and "Do the arrows look right?" in asks[1]
    assert not any("early words" in a["text"] for a in g.answers)         # a line before the question does not count


def test_lines_after_the_answer_window_are_the_next_answer(tmp_path):
    g, s, _ = guide(tmp_path, [(1, "join"), (20, chat("Lars", "the arrows")), (25, chat("Lars", "start low")),
                               (20 + play_guide.MORE + 10, chat("Lars", "title is fine"))])
    list(g.run())
    assert [a["text"] for a in g.answers] == ["the arrows start low", "title is fine"]


def test_names_give_buildings_their_target_and_units_their_uuid():
    objs = [{"kind": "building", "name": "BARRACKS", "player": 1, "footprint": [72, 44, 84, 56]},
            {"kind": "unit", "name": "MILITIA", "player": 1, "uuid": "m-1"},
            {"kind": "unit", "name": "MILITIA", "player": 1, "uuid": "m-1b"},
            {"kind": "unit", "name": "MILITIA", "player": 2, "uuid": "m-2"},
            {"kind": "building", "name": "TOWN_CENTER", "player": 2, "footprint": [136, 136, 152, 152]},
            {"kind": "object", "name": "TREE_OAK", "player": 0}]
    n = play_guide.names(objs)
    assert n["{BARRACKS}"] == n["{BARRACKS1}"] == combat.target_uuid([72, 44, 84, 56])
    assert n["{MILITIA}"] == n["{MILITIA1}"] == "m-1" and n["{MILITIA2}"] == "m-2"
    assert n["{TOWN_CENTER2}"] == combat.target_uuid([136, 136, 152, 152]) and "{TOWN_CENTER}" not in n
    assert play_guide.fill("kill {MILITIA2} {X}", n) == "kill m-2 {X}"


def test_the_guide_finds_the_server_of_a_game_port(tmp_path):
    for k, (game, rcon) in enumerate(((25601, 25701), (25602, 25702))):
        d = tmp_path / f"tmp{k}"
        d.mkdir()
        (d / "server.properties").write_text(f"server-port={game}\nrcon.port={rcon}\nrcon.password=pw{k}\n")
    assert play_guide.server(25602, str(tmp_path)) == (str(tmp_path / "tmp1"), 25702, "pw1")
    with pytest.raises(SystemExit):
        play_guide.server(1, str(tmp_path))


def test_the_bot_wave_meets_the_town_center_first(tmp_path):
    """owner_loop: the nearest units of player 1 to each soldier of the bot are the villagers at the town center
    (bot.fight attacks the nearest unit), not the militia at the dock: so the arrows of #1204 shoot (session fault)."""
    path = scenarios.owner_loop(str(tmp_path / "loop.aoe2scenario"))
    with contextlib.redirect_stdout(io.StringIO()):
        um = AoE2DEScenario.from_file(path).unit_manager
    p1, p2 = um.units[1], um.units[2]
    tc = next(u for u in p1 if u.unit_const == BuildingInfo.TOWN_CENTER.ID)
    soldiers = [u for u in p2 if u.unit_const == UnitInfo.MILITIA.ID]
    mine = [u for u in p1 if u.unit_const in (UnitInfo.VILLAGER_MALE.ID, UnitInfo.VILLAGER_FEMALE.ID,
                                              UnitInfo.MILITIA.ID, UnitInfo.TRANSPORT_SHIP.ID)]
    assert len(soldiers) == 5 and any(u.unit_const == BuildingInfo.DOCK.ID for u in p1)
    for s in soldiers:
        near = min(mine, key=lambda u: math.dist((u.x, u.y), (s.x, s.y)))
        assert math.dist((near.x, near.y), (tc.x, tc.y)) < 5, (s.x, s.y, near.unit_const)


def test_owner_tasks_plan_puts_each_ticket_in_one_game_or_none():
    import owner_tasks
    issues = [{"number": n, "title": t, "body": b, "labels": [{"name": "needs-human"}], "state": "open"} for n, t, b in (
        (1, "Check the replay follow camera", ""), (2, "Check the bot of player 2 in Minecraft", ""),
        (3, "Check the jumps", "Watch: 03:00 | chopper | Does it chop?"), (4, "Decide: the cheats", ""),
        (5, "Show a panel", ""))]
    comments = {5: [{"body": "@Larspolo All criteria are met. Please close it."}]}
    got = owner_tasks.plan(owner_tasks.tasks(issues, comments))
    assert list(got) == list(owner_tasks.PLAN)
    assert {g: [t["number"] for t in ts] for g, ts in got.items()} == \
        {"close now": [5], "replay": [1, 3], "play game": [2], "no game": [4]}
