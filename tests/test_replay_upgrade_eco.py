"""Live replay: the economy and University researches of each player in the sky (#3790). Fake RCON."""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "game"))
import replay  # noqa: E402
from test_replay import Fake, data  # noqa: E402


def rows(cmd):
    return json.loads(cmd[cmd.index("text:") + 5:].split(",billboard")[0].removesuffix("}"))


def test_the_economy_lines_follow_their_after_chain():
    wood = next((line, len(techs)) for line, techs in replay.ECO_LINES if "DOUBLE_BIT_AXE" in techs)
    r = replay.Replay(Fake(), data([]))
    r.learn({"player": 1, "technology": "Double-Bit Axe", "time": 1000})
    r.learn({"player": 1, "technology": "Bow Saw", "time": 2000})
    cmds = r.upgrade_view(3000)
    assert len(cmds) == 1 and f'"{replay.UPGRADE_ECO}"' in cmds[0]
    assert f"{wood[0]} 2/{wood[1]}" in rows(cmds[0])[1]["text"]


def test_the_university_row_shows_the_labels_and_stays_below_the_rcon_limit():
    r = replay.Replay(Fake(), data([]))
    r.learn({"player": 1, "technology": "Ballistics", "time": 1000})
    cmds = r.upgrade_view(2000)
    uni = [c for c in cmds if f'"{replay.UPGRADE_UNI}"' in c]
    assert len(uni) == 1 and "Ballistics" in rows(uni[0])[1]["text"]


def test_all_upgrades_of_eight_players_stay_below_the_rcon_limit():
    d = data([])
    d["players"] = {str(p): {"civ": "BYZANTINES", "color": p} for p in range(9)}
    r = replay.Replay(Fake(), d)
    for p in range(1, 9):
        for label in replay.TECHS:
            r.learn({"player": p, "technology": label, "time": 0})
    cmds = r.upgrade_view(0)
    assert len(cmds) == 3                                               # the Blacksmith, economy and University rows
    assert all(len(c.encode()) < 1446 for c in cmds)
