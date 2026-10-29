"""Two people (#1310): each Minecraft player selects and orders only the units of its own AoE2 player. Each Gather
reads and serves only the Minecraft players of its team p<player>; run.py gives the sides in the join order (#1308)."""
import math
import re

from test_gather import grid

from game import gather, run

PITCH = math.degrees(math.atan2(0.62, 3))                              # from 3 blocks away down at the head of a unit
TEAMS = {"Steve": 1, "Alex": 2}


class TwoServer:
    """Answers the commands of two Gathers; Steve is on team p1, Alex on team p2."""

    def __init__(self, entities):
        self.entities, self.log, self.scores = entities, [], {}       # scores: (name, objective) -> 1

    def command(self, cmd):
        self.log.append(cmd)
        if m := re.fullmatch(r"data get entity (\S+) (Pos|Rotation)", cmd):
            if m[1] not in self.entities:
                return "No entity was found"
            return f"{m[1]} has the following entity data: [{', '.join(f'{x}d' for x in self.entities[m[1]][m[2]])}]"
        if m := re.fullmatch(r"execute if entity @a\[team=p(\d),scores=\{(\w+)=1\.\.\}\]", cmd):
            hit = any(TEAMS[n] == int(m[1]) and o == m[2] for n, o in self.scores)
            return "Test passed, count: 1" if hit else "Test failed"
        if m := re.fullmatch(r"execute if entity @a\[team=p(\d),name=(\w+)\]", cmd):
            return "Test passed, count: 1" if TEAMS.get(m[2]) == int(m[1]) else "Test failed"
        if cmd == "list":
            return "There are 2 of a max of 20 players online: Steve, Alex"
        if m := re.fullmatch(r"scoreboard players get (\w+) (\w+)", cmd):
            return f"{m[1]} has {self.scores.get((m[1], m[2]), 0)} [{m[2]}]"
        if m := re.fullmatch(r"scoreboard players reset (\w+) (\w+)", cmd):
            self.scores.pop((m[1], m[2]), None)
        return ""


def setup():
    """A flat map with villager "a" of player 1 and villager "b" of player 2, both with a Gather of its team."""
    objects = [{"kind": "unit", "name": "VILLAGER_MALE", "player": 1, "uuid": "a", "tile": [6.5, 10.5]},
               {"kind": "unit", "name": "VILLAGER_MALE", "player": 2, "uuid": "b", "tile": [14.5, 10.5]}]
    server = TwoServer({o["uuid"]: {"Pos": (o["tile"][0], 64.0, o["tile"][1])} for o in objects})
    out = []
    for player in (1, 2):
        g = gather.Gather(server, grid([[64] * 24 for _ in range(24)], objects), player=player)
        g.who = f"@a[team=p{player}]"
        out.append(g.setup())
    return server, *out


def click(server, name, uuid):
    """Minecraft player name stands 3 blocks north of unit uuid, looks at it and right clicks."""
    x, y, z = server.entities[uuid]["Pos"]
    server.entities[name] = {"Pos": (x, y, z - 3), "Rotation": (0.0, PITCH)}
    server.scores[(name, "aoe_use")] = 1


def run_clicks(*gs):
    for g in gs:
        for name in g.clicks():
            g.click(name)


def test_a_click_of_the_player_of_team_p2_selects_only_a_villager_of_player_2():
    server, g1, g2 = setup()
    assert g1.villagers.keys() == {"a"} and g2.villagers.keys() == {"b"}
    click(server, "Alex", "a")                                         # a villager of player 1
    run_clicks(g1, g2)
    assert not g1.selected and not g2.selected and not server.scores
    click(server, "Alex", "b")
    run_clicks(g1, g2)
    assert g2.selected == {"b"} and not g1.selected


def test_a_click_of_the_player_of_team_p1_goes_only_to_the_gather_of_player_1():
    server, g1, g2 = setup()
    click(server, "Steve", "a")
    assert g2.clicks() == [] and ("Steve", "aoe_use") in server.scores   # player 2 does not read or reset it
    assert g1.clicks() == ["Steve"]
    g1.click("Steve")
    assert g1.selected == {"a"} and not g2.selected


def test_each_gather_gives_its_items_and_menu_only_to_its_team():
    server, g1, g2 = setup()
    server.log.clear()
    g2.clicks()
    gives = [c for c in server.log if c.startswith(("execute as", "scoreboard players enable"))]
    assert gives and all("@a[team=p2]" in c for c in gives)
    assert not any("team join p2 @a" in c or "team join p1" in c for c in server.log)


def test_the_join_order_gives_the_sides():
    game = run.Game.__new__(run.Game)
    game.people, game.sides, sent = 2, {}, []
    game.command = sent.append
    for name in ("Alex", "Steve", "Bob", "Alex"):                     # Alex joins again after Bob
        game.side(name)
    assert game.sides == {"Alex": 1, "Steve": 2}
    sent = [c for c in sent if not c.startswith("tellraw")]   # the chat hint (#3555) is no join command
    assert sent == ["team join p1 Alex", "aoe hide Alex team", "team join p2 Steve", "aoe hide Steve team", *run.SPECTATORS, "team join spec Bob",
                    "gamemode spectator Bob", "aoe show Bob all", "team join p1 Alex", "aoe hide Alex team"]    # Bob watches (#2898, #2921)


def test_one_person_keeps_all_players_on_team_p1():
    game = run.Game.__new__(run.Game)
    game.sides, sent = {}, []
    game.command = sent.append
    game.side("Steve")
    assert game.people == 1 and not game.sides and not sent
    g = gather.Gather(None, grid([[64] * 4 for _ in range(4)]))
    assert g.who == "@a" and gather.only(g.who, "name=!Steve") == "@a[name=!Steve]"
    assert gather.only("@a[team=p2]", "name=!Steve") == "@a[team=p2,name=!Steve]"


def test_the_join_line_of_paper_26_3_counts():
    line = "[09:50:50 INFO]: System chat: \x1b[93mone joined the game\x1b[0m"            # from a real server
    assert run.JOINED.search(line).group(1) == "one"
    assert not run.JOINED.search("[09:50:50 INFO]: <one> System chat: two joined the game")
