"""Live replay: the score panel and the summary group the players by team (#1189). Fake RCON."""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "game"))
import lang  # noqa: E402
import replay  # noqa: E402
from test_replay import Fake, data  # noqa: E402


def game(teams):
    d = data([])
    civs = ("BRITONS", "AZTECS", "FRANKS", "MONGOLS")
    d["players"] = {str(p): {"civ": civs[p - 1], "color": "blue", "arch": "western", "team": t}
                    for p, t in teams.items()}
    r = replay.Replay(Fake(), d)
    r.pop = {p: 2 + p for p in teams}
    return r


def lines(cmds):
    """The player name of each tellraw line, in order."""
    return ["".join(lang.plain(t) for t in json.loads(c.split(" ", 2)[2])).split(":")[0]
            for c in cmds if c.startswith("tellraw @a [")]


def test_a_2_against_2_panel_keeps_each_team_together():
    r = game({1: 1, 2: 2, 3: 1, 4: 2})
    cmds = r.score_commands()
    scores = {c.split()[3]: int(c.split()[5]) for c in cmds if c.startswith("scoreboard players set ")}
    assert sorted(scores, key=scores.get, reverse=True) == ["P3", "P1", "P4", "P2"]      # the sidebar order
    assert min(scores["P1"], scores["P3"]) > max(scores["P2"], scores["P4"])
    fixed = [c for c in cmds if " numberformat " in c]
    assert fixed[0] == 'scoreboard players display numberformat P1 aoe_pop fixed {"text": "3"}' and len(fixed) == 4
    names = [json.loads(c.split(" ", 6)[6])["text"] for c in cmds if " display name " in c]
    assert names[0].startswith("Team 1 · Player 1 (Britons) · Dark") and names[1].startswith("Team 2 · Player 2")


def test_a_2_against_2_summary_lists_team_1_then_team_2():
    r = game({1: 1, 2: 2, 3: 1, 4: 2})
    names = lines(r.summary_commands())
    assert names[:4] == ["Team 1 · Player 1 (Britons)", "Team 1 · Player 1 (Britons)",
                         "Team 1 · Player 3 (Franks)", "Team 1 · Player 3 (Franks)"]
    assert names[4] == "Team 2 · Player 2 (Aztecs)"
    assert lines(r.tech_commands()) == ["Team 1 · Player 1 (Britons)", "Team 1 · Player 3 (Franks)",
                                        "Team 2 · Player 2 (Aztecs)", "Team 2 · Player 4 (Mongols)"]


def test_a_1_against_1_game_shows_the_same_lines_as_before():
    for teams in ({1: 1, 2: 2}, {1: None, 2: None}):
        r = game(teams)
        cmds = r.score_commands()
        assert [c for c in cmds if c.startswith("scoreboard players set ")] == ["scoreboard players set P1 aoe_pop 3",
                                                                                "scoreboard players set P2 aoe_pop 4"]
        assert not any(" numberformat " in c for c in cmds)
        assert lines(r.tech_commands()) == ["Player 1 (Britons)", "Player 2 (Aztecs)"]
