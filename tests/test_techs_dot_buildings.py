"""The damage over time of the arrows of the defensive buildings (#4641): with a rule of the key "damage_over_time" of
data/train.jsonl for a building (Curare: towers and castles), its "aoe building" command gets the last field
"dot=damage:ticks:classes", and the plugin starts the rule when an arrow of the building hits (Dot.java)."""
from pathlib import Path

from test_techs_damage_over_time import patch, tail
from test_techs_persians import castle_commands, hp_setup

from game import build, combat

RULE = {"if": [{"names": ["CASTLE"]}], "damage": 7.5, "seconds": 15}
UUID = combat.target_uuid([10, 2, 14, 6])
BOX = (10, 64, 2, 13, 70, 5)
PLUGIN = Path(__file__).parent.parent / "game/plugin/src/main/java/aoe2mc/AoePlugin.java"


def test_the_building_command_has_the_rule_only_when_the_building_shoots():
    plain = combat.building(UUID, "CASTLE", 1, BOX)
    rule = combat.building(UUID, "CASTLE", 1, BOX, dot=(7.5, 15, ()))
    ticks = max(1, round(15 / combat.NORMAL * 20))
    assert rule[:-1] == plain[:-1] and rule[-1] == plain[-1] + f" dot=7.5:{ticks}:-"
    assert tail(rule[-1]) == ["7.5", str(ticks), "-"]
    house = (10, 64, 2, 11, 70, 3)
    assert combat.building(UUID, "HOUSE", 1, house, dot=(7.5, 15, ())) == combat.building(UUID, "HOUSE", 1, house)


def test_a_research_sends_the_rule_to_the_castle_of_the_player(monkeypatch):
    tech = patch(monkeypatch, [RULE])
    server, g = hp_setup()
    before = set(g.techs)
    g.techs.add(tech)
    build.retower(g, before)
    sent = castle_commands(server)
    assert sent and tail(sent[-1])[0] == f"{RULE['damage']:g}"


def test_with_no_rule_the_research_sends_nothing(monkeypatch):
    tech = patch(monkeypatch, [{"if": [{"names": ["KNIGHT"]}], "damage": 1, "seconds": 1}])
    server, g = hp_setup()
    before = set(g.techs)
    g.techs.add(tech)
    build.retower(g, before)
    assert castle_commands(server) == []


def test_the_plugin_starts_the_rule_of_the_building_at_the_hit_of_its_arrow():
    src = PLUGIN.read_text()
    command = src[src.index("Dot.Rule fortDot"):src.index('sender.sendMessage("Buildings: "')]
    assert 'startsWith("dot=")' in command and "dots.set(le.getUniqueId(), fortDot)" in command
    hit = src[src.index("double dealt = harm(victim, t, a, fort != null"):]
    assert "dots.start(from, victim, t.classes())" in hit[:hit.index("double[] through")]
