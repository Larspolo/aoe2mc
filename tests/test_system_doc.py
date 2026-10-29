"""docs/SYSTEM.md: each file of the table "Generic and specific files" exists (#904)."""
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def table_paths():
    with open(os.path.join(ROOT, "docs", "SYSTEM.md")) as f:
        text = f.read()
    part = text.split("## Generic and specific files", 1)[1]
    return re.findall(r"^\| `([^`]+)` \| (?:generic|specific) \|", part, re.M)


def test_the_table_has_the_system_files():
    paths = table_paths()
    for p in ("CLAUDE.md", "tools/claim.py", ".claude/skills/autopilot/SKILL.md", ".github/workflows/automerge.yml"):
        assert p in paths


def test_each_file_of_the_table_exists():
    missing = [p for p in table_paths() if not os.path.exists(os.path.join(ROOT, p))]
    assert not missing


def test_each_skill_and_workflow_is_in_the_table():
    paths = set(table_paths())
    skills = {f".claude/skills/{d}/SKILL.md" for d in os.listdir(os.path.join(ROOT, ".claude", "skills"))}
    flows = {f".github/workflows/{f}" for f in os.listdir(os.path.join(ROOT, ".github", "workflows"))
             if f != "worlds.yml"}                                  # releases of worlds: not a part of the agent loop
    missing = (skills | flows) - paths
    assert not missing, f"add a row for each of {sorted(missing)} to the table 'Generic and specific files' of docs/SYSTEM.md"
