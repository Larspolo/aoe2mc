"""The command /controls (#5501): the trigger score gives the control lines to that player only and resets it."""
import json
import re

import controls
import lang


class G:
    who = "@a"

    def __init__(self, scores):
        self.scores, self.sent = dict(scores), []

    def people(self):
        return list(self.scores)

    def command(self, c):
        self.sent.append(c)
        if c.startswith("execute if entity"):
            return "Test passed" if any(self.scores.values()) else "Test failed"
        if m := re.match(r"scoreboard players get (\S+) ", c):
            return f"{m[1]} has {self.scores[m[1]]} [aoe_controls]"
        if m := re.match(r"scoreboard players set (\S+) \S+ (\d+)", c):
            self.scores[m[1]] = int(m[2])
        return ""


def lines(g, name):
    return [json.loads(c.split(" ", 2)[2]) for c in g.sent if c.startswith(f"tellraw {name} ")]


def test_score_gives_lines_to_that_player_and_resets():
    g = G({"alice": 1, "bob": 0})
    controls.tick(g)
    got = lines(g, "alice")
    assert [t["translate"] for t in got] == controls.keys()
    assert [t["fallback"] for t in got] == [lang.en_us()[k] for k in controls.keys()]
    assert lines(g, "bob") == [] and g.scores["alice"] == 0
    g.sent.clear()
    controls.tick(g)
    assert lines(g, "alice") == []


def test_trigger_is_enabled_for_non_operators():
    g = G({"alice": 0})
    controls.tick(g)
    assert f"scoreboard players enable @a {controls.OBJECTIVE}" in g.sent


def test_plugin_registers_command_without_permission():
    yml = open("game/plugin/src/main/resources/plugin.yml").read()
    block = yml.split("\n  controls:\n")[1].split("\npermissions:")[0]
    assert "permission:" not in block
    assert f'getObjective("{controls.OBJECTIVE}")' in open("game/plugin/src/main/java/aoe2mc/AoePlugin.java").read()
