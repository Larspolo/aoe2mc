"""docs/SYSTEM.md: each file of the table "Generic and specific files" and of framework/files.txt exists (#904, #4192)."""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import bootstrap  # noqa: E402


def table_paths():
    return [p for p, _ in bootstrap.rows()]


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
