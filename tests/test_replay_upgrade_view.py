"""Live replay: the Blacksmith tiers of each player in the sky (#3786). Fake RCON."""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "game"))
import replay  # noqa: E402
from test_replay import Fake, data  # noqa: E402


def rows(cmd):
    return json.loads(cmd[cmd.index("text:") + 5:].split(",billboard")[0].removesuffix("}"))


def test_the_tiers_show_once_and_change_with_a_research():
    r = replay.Replay(Fake(), data([]))
    assert [line for line, _ in replay.SMITH] == ["Melee", "Infantry armor", "Archer", "Archer armor", "Cavalry armor"]
    r.learn({"player": 1, "technology": "Forging", "time": 1000})
    first = r.upgrade_view(2000)
    assert len(first) == 1 and first[0].startswith("summon text_display") and f'"{replay.UPGRADE}"' in first[0]
    lines = [x["text"] for x in rows(first[0])]
    assert lines[1].endswith(": Melee 1/3 · Infantry armor 0/3 · Archer 0/3 · Archer armor 0/3 · Cavalry armor 0/3\n")
    assert "Melee 0/3" in lines[2] and len(lines) == 3                  # the title, 2 players
    assert r.upgrade_view(3000) == []                                   # no new research: no command
    r.learn({"player": 1, "technology": "Iron Casting", "time": 4000})
    assert r.upgrade_view(3500) == []                                   # not yet at this game time
    second = r.upgrade_view(5000)
    assert len(second) == 1 and second[0].startswith(f"data merge entity @e[type=text_display,tag={replay.UPGRADE},")
    assert "Melee 2/3" in rows(second[0])[1]["text"]


def test_eight_players_stay_below_the_rcon_limit():
    d = data([])
    d["players"] = {str(p): {"civ": "BYZANTINES", "color": p} for p in range(9)}
    r = replay.Replay(Fake(), d)
    assert r.upgrade_view(0) == []                                      # no research yet: no display
    r.learn({"player": 3, "technology": "Forging", "time": 0})
    cmd = r.upgrade_view(0)[0]
    assert len(cmd.encode()) < 1446
