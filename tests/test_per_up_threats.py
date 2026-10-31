"""The threat commands of an AI script (#4966): an enemy soldier hits a bot villager in the town (Bot.guard ->
Bot.hits -> Script.hit), then up-attacker-class, up-get-attacker-class, up-get-threat-data, up-projectile-detected,
up-projectile-target and up-get-projectile-player read the class, the time and the player. The map of test_bot_gather
(player 1 a person, the bot is player 2)."""
from test_bot_gather import bot_map

from game import per
from game.bot import build, train  # noqa: F401  the modules that per uses

RULES = """
(defrule (up-attacker-class == {source}) => (set-goal 1 1))
(defrule (true) => (up-get-attacker-class 2) (up-get-threat-data 3 4 5 6) (up-get-projectile-player {shot} 7))
(defrule (up-projectile-detected {shot} < 5000) => (set-goal 8 1))
(defrule (up-projectile-target {shot} == {target}) => (set-goal 9 1))
"""


def attack(name):
    """An enemy unit of player 1 next to bot villager b0, one look of guard(), then one pass of the script."""
    server, me, b = bot_map()
    me.bots = [b]
    source, target = per.klass(name), per.klass("VILLAGER_MALE")
    b.script = s = per.Script(per.parse(RULES.format(source=source, target=target, shot="projectile-any")), b)
    s.step()
    assert s.goals.get(2) == -1 and s.goals.get(7) == -1 and 8 not in s.goals         # no hit yet
    server.entities["e1"] = {"Pos": (25.5, 64.0, 19.5), "Rotation": (0.0, 0.0)}
    b.g.data["objects"].append({"kind": "unit", "name": name, "player": 1, "uuid": "e1", "tile": [25.5, 19.5]})
    b.g.enemies["e1"] = name
    b.guarded = b.time = 10.0
    b.guard()
    b.time = 11.5
    s.step()
    return s, source, target


def test_an_archer_hit_gives_the_class_time_player_and_projectile():
    s, source, target = attack("ARCHER")
    assert source != -1 and target != -1 and source != target
    assert s.goals[1] == 1 and s.goals[2] == source
    assert [s.goals[g] for g in (3, 4, 5, 6)] == [1500, 1, source, target]
    assert s.goals[7] == 1 and s.goals[8] == 1 and s.goals[9] == 1
    assert not s.warned


def test_a_melee_hit_is_a_threat_but_no_projectile():
    s, source, target = attack("MILITIA")
    assert s.goals[1] == 1 and [s.goals[g] for g in (3, 4, 5, 6)] == [1500, 1, source, target]
    assert s.goals[7] == -1 and 8 not in s.goals and 9 not in s.goals


def test_an_unknown_projectile_type_warns_once():
    server, me, b = bot_map()
    s = per.Script(per.parse("(defrule (up-projectile-detected projectile-laser < 1) => (set-goal 1 1))"), b)
    s.step()
    s.step()
    assert s.warned == {("projectile type", "projectile-laser")} and 1 not in s.goals
