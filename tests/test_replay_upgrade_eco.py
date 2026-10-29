"""Live replay: the economy and University researches of each player in the book "Upgrades" (#3790, #3924). Fake RCON."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "game"))
import replay  # noqa: E402
from test_replay import Fake, data  # noqa: E402
from test_replay_stat_books import page, pages  # noqa: E402


def test_the_economy_lines_follow_their_after_chain():
    wood = next((line, len(techs)) for line, techs in replay.ECO_LINES if "DOUBLE_BIT_AXE" in techs)
    r = replay.Replay(Fake(), data([]))
    r.learn({"player": 1, "technology": "Double-Bit Axe", "time": 1000})
    r.learn({"player": 1, "technology": "Bow Saw", "time": 2000})
    assert f"{wood[0]} 2/{wood[1]}" in page(r.upgrade_view(3000), 0)


def test_the_university_lines_show_the_labels():
    r = replay.Replay(Fake(), data([]))
    r.learn({"player": 1, "technology": "Ballistics", "time": 1000})
    lines = " ".join(pages(r.upgrade_view(2000)))
    assert "University:" in lines and "Ballistics" in lines


def test_all_upgrades_of_eight_players_stay_below_the_rcon_limit():
    d = data([])
    d["players"] = {str(p): {"civ": "BYZANTINES", "color": p} for p in range(9)}
    r = replay.Replay(Fake(), d)
    for p in range(1, 9):
        for label in replay.TECHS:
            r.learn({"player": p, "technology": label, "time": 0})
    cmds = r.upgrade_view(0)
    assert len(pages(cmds)) >= 8 and all(len(c.encode()) <= replay.RCON_MAX for c in cmds)
