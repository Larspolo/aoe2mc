"""Goal 4 of steering/project/ROADMAP.md is the agent system (#900): it has its rows, and the release total counts only the game goals."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools"))
import release  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def test_goal_4_is_the_agent_system():
    with open(os.path.join(ROOT, "steering", "project", "ROADMAP.md")) as f:
        features = release.roadmap(f.read())
    keys = {k for k, v in features.items() if v[0] == 4}
    assert keys and all(k.startswith("system:") for k in keys)
    assert release.lines({4: {"C": (50, 1, 1, 0, 0)}})[0].startswith("Agent system: C 50 %")


def test_the_total_skips_the_agent_system():
    game = {1: {"C": (50, 5, 5, 0, 0)}}
    assert release.total(game) == 50
    assert release.total({**game, 4: {"C": (0, 0, 10, 0, 3)}}) == 50
