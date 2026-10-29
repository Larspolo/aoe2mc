"""Two people (#1937, epic #1306): the per-player parts of the game program work for player 2 at the same time as for
player 1. Each part sends its commands for player 2 only to @a[team=p2], and changes only the state of player 2:
control groups, cheat codes, the boss bar, the hints, the team of the attack alerts, the population, an age and a
technology."""
import json
import re

from test_gather import grid
from test_two_players import TEAMS, TwoServer, click, run_clicks

from game import bossbar, cheats, gather, train

P1, P2 = "@a[team=p1]", "@a[team=p2]"


class PartServer(TwoServer):
    """TwoServer, and each Minecraft player can hold a control group item (hand: name -> group) and sneak."""

    def __init__(self, entities):
        super().__init__(entities)
        self.hand, self.sneak = {}, set()

    def command(self, cmd):
        if m := re.fullmatch(r"execute if items entity (\w+) weapon\.mainhand \*\[custom_data=\{aoe_group:(\d)\}\]", cmd):
            self.log.append(cmd)
            return "Test passed, count: 1" if self.hand.get(m[1]) == int(m[2]) else "Test failed"
        if m := re.fullmatch(r"execute as (\w+) if predicate .*is_sneaking.*", cmd):
            return "Test passed" if m[1] in self.sneak else "Test failed"
        return super().command(cmd)


def setup(**kw):
    """A flat map: a town center and villager "a" of player 1, a town center and villager "b" of player 2."""
    objects = [{"kind": "unit", "name": "VILLAGER_MALE", "player": 1, "uuid": "a", "tile": [6.5, 10.5]},
               {"kind": "unit", "name": "VILLAGER_MALE", "player": 2, "uuid": "b", "tile": [14.5, 10.5]},
               {"kind": "building", "name": "TOWN_CENTER", "player": 1, "tile": [3.5, 3.5], "footprint": [2, 2, 5, 5]},
               {"kind": "building", "name": "TOWN_CENTER", "player": 2, "tile": [19.5, 3.5],
                "footprint": [18, 2, 21, 5]}]
    server = PartServer({o["uuid"]: {"Pos": (o["tile"][0], 64.0, o["tile"][1])} for o in objects if "uuid" in o})
    out = []
    for player in (1, 2):
        g = gather.Gather(server, grid([[64] * 24 for _ in range(24)], objects), player=player, **kw)
        g.who = f"@a[team=p{player}]"
        out.append(g.setup())
    server.log.clear()
    return server, *out


def test_a_control_group_of_player_2_goes_only_to_its_team_and_its_gather():
    server, g1, g2 = setup()
    click(server, "Alex", "b")
    run_clicks(g1, g2)
    server.hand["Alex"], server.sneak = 2, {"Alex"}
    server.scores[("Alex", "aoe_use")] = 1
    server.log.clear()
    run_clicks(g1, g2)                                                 # Alex: shift + click on the item of group 2
    assert g2.groups == {2: {"b"}} and not g1.groups
    assert f"item replace entity Alex hotbar.5 with {gather.group_item(2, 1)}" in server.log   # its person (#3490)
    assert any(c.startswith("title Alex actionbar") and "Group 2: 1 units saved" in c for c in server.log)
    assert not any(P1 in c or "Steve" in c for c in server.log if "aoe_group" in c or "actionbar" in c)
    g2.choose(set())
    server.sneak = set()
    server.scores[("Alex", "aoe_use")] = 1
    run_clicks(g1, g2)                                                 # a click: select the group
    assert g2.selected == {"b"} and not g1.selected and not g1.groups
    server.log.clear()
    g2.calls = 0
    g2.clicks()                                                        # the group items of the hotbar
    give = [c for c in server.log if "aoe_group" in c and "item replace" in c]
    assert len(give) == len(gather.GROUPS) and all(c.startswith("execute as Alex ") for c in give)   # its person (#3490)
    assert "Group 2: 1 unit" in next(c for c in give if "hotbar.5" in c)


def test_a_cheat_of_the_person_of_player_2_changes_only_player_2():
    server, g1, g2 = setup(cheats=True)
    wood = g1.stock["wood"]
    server.scores[("Alex", "aoe_cheat")] = cheats.NAMES.index("lumberjack") + 1
    assert cheats.clicks(g1) == [] and ("Alex", "aoe_cheat") in server.scores   # player 1 does not read or reset it
    assert cheats.clicks(g2) == [("Alex", "lumberjack")] and not server.scores
    assert g2.stock["wood"] == wood + 10000 and g1.stock["wood"] == wood
    assert any(c.startswith("scoreboard players") and "Wood aoe_res2" in c for c in server.log)
    assert not any(re.search(r"\baoe_res\b", c) for c in server.log)  # not the sidebar of player 1
    server.scores[("Steve", "aoe_cheat")] = cheats.NAMES.index("polo") + 1
    assert cheats.clicks(g2) == [] and cheats.clicks(g1) == [("Steve", "polo")]
    assert server.log[-1] == 'tellraw Steve {"text":"Fog of war: off"}'


def test_the_boss_bar_of_player_2_shows_its_selection_only_to_its_team():
    server, g1, g2 = setup()
    click(server, "Alex", "b")
    run_clicks(g1, g2)
    assert g2.bar == "b" and g1.bar is None
    bars = [c for c in server.log if c.startswith("bossbar") or "bossbar" in c.split(" run ")[0]]
    assert bars and all(bossbar.bar(g2) in c for c in bars)            # aoe2mc:sel_p2, not the bar of player 1
    assert f"bossbar set {bossbar.bar(g2)} players {P2}" in server.log
    assert f"bossbar set {bossbar.bar(g2)} visible true" in server.log
    assert bossbar.bar(g1) != bossbar.bar(g2)


def test_the_hints_of_player_2_go_only_to_its_team():
    server, g1, g2 = setup()
    g1.clicks()                                                        # player 1 has no selection: its own hint
    hints = [c for c in server.log if " actionbar " in c]
    assert len(hints) == 1 and hints[0].startswith(f"title {P1} actionbar ") and "Right click: select a unit" in hints[0]
    click(server, "Alex", "b")
    run_clicks(g1, g2)
    server.log.clear()
    g1.clicks()
    g2.clicks()
    hints = [c for c in server.log if " actionbar " in c]
    text = "1 villager · Right click: gather, build, build menu · Empty box: deselect"
    assert hints == [f"title {P2} actionbar " + json.dumps({"text": text, "color": "gray"})]   # p1: the idle hint once


def test_each_person_joins_only_the_team_of_its_player_for_the_attack_alerts():
    server, g1, g2 = setup()
    assert not any(c.startswith("team join") for c in server.log)     # not "team join p2 @a" (#1241)
    for g in (g1, g2):
        g.point()
    joins = [c for c in server.log if c.startswith("team join")]
    assert joins == ["team join p1 Steve", "team join p2 Alex"] and TEAMS == {"Steve": 1, "Alex": 2}
    server.log.clear()
    g2.point()
    assert not any(c.startswith("team join") for c in server.log)     # once per person


def test_player_2_trains_ages_and_researches_without_a_change_for_player_1():
    server, g1, g2 = setup()
    for g in (g1, g2):
        g.stock.update(food=2000, wood=2000, gold=2000, stone=2000)
    assert train.queue(g2, "Alex", (19, 3)) == (18, 21, 2, 5)          # the own town center
    assert train.queue(g2, "Alex", (3, 3)) is None                     # not the town center of player 1
    assert train.queue(g2, "Alex", (19, 3), "LOOM") == (18, 21, 2, 5)
    assert g2.stock["food"] == 2000 - 50 and g1.stock["food"] == 2000
    for _ in range(round((train.TRAIN_TIMES["VILLAGER_MALE"] + 30) / 0.5) + 1):
        for v in train.tick(g2, 0.5):
            server.entities[v.uuid] = {"Pos": v.pos}
    assert g2.pop == 2 and g1.pop == 1 and "LOOM" in g2.techs and not g1.techs
    assert "scoreboard players set Population aoe_res2 2" in server.log
    assert not any(re.search(r"\baoe_res\b", c) for c in server.log)
    assert 'tellraw Alex {"text": "Loom is researched.", "color": "green"}' in server.log
    g2.data["objects"] += [{"kind": "building", "name": n, "player": 2, "tile": [12.5, 2.5 + 3 * i],
                            "footprint": [11, 1 + 3 * i, 14, 4 + 3 * i]} for i, n in enumerate(("BARRACKS", "MILL"))]
    server.log.clear()
    assert train.queue(g2, "Alex", (19, 3), "FEUDAL_AGE") == (18, 21, 2, 5)
    train.tick(g2, 130)
    assert train.age(g2) == "Feudal Age" and train.age(g1) == "Dark Age"
    assert 'title @a[team=p2] title {"text": "Feudal Age", "color": "gold"}' in server.log
    assert 'scoreboard objectives modify aoe_res2 displayname "Resources (Feudal Age)"' in server.log
    assert not any(P1 in c or re.search(r"\baoe_res\b", c) for c in server.log)
    assert any(c.startswith("tellraw @a") and "Player 2 advances to the Feudal Age." in c for c in server.log)
