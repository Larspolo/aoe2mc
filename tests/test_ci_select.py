"""tools/ci_select.py: a Markdown-only PR runs only the doc tests in the quick CI job (#2089)."""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import ci_select  # noqa: E402


def test_a_code_change_runs_all_tests():
    assert ci_select.select(["aoe2mc.py"]) is None
    assert ci_select.select(["docs/LEARNINGS.md", "framework/tools/claim.py"]) is None
    assert ci_select.select(["game/data/train.jsonl"]) is None
    assert ci_select.select([]) is None


def test_a_markdown_change_runs_the_doc_tests():
    tests = ci_select.select(["docs/LEARNINGS.md", ".claude/skills/autopilot/SKILL.md"])
    # Direct readers of a Markdown file, and a test that reads one through a tool (release.py: steering/project/RELEASE.md).
    for t in ("test_learnings.py", "test_system_doc.py", "test_autopilot_skill.py", "test_generic_words.py",
              "test_feature_table.py", "test_coverage.py", "test_release.py", "test_ci_select.py"):
        assert f"tests/{t}" in tests
    assert "tests/test_terrain.py" not in tests


def test_imports():
    text = "import os, json\nfrom tools import claim, usage as u\nimport release\n"
    assert {"os", "json", "tools.claim", "tools.usage", "release"} <= ci_select.imports(text)
