"""The autopilot skill: a short main file, the rare cases in named files next to it (#1700)."""
import os
import re

DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".claude", "skills", "autopilot")


def test_the_main_file_is_short():
    assert os.path.getsize(os.path.join(DIR, "SKILL.md")) < 12 * 1024


def test_each_part_is_named_in_the_main_file_and_exists():
    with open(os.path.join(DIR, "SKILL.md")) as f:
        named = set(re.findall(r"^\| `(\w+\.md)` \|", f.read(), re.M))
    parts = {f for f in os.listdir(DIR) if f.endswith(".md") and f != "SKILL.md"}
    assert named == parts
