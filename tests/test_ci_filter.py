"""CI runs the Minecraft tests on a PR only when the PR changes a file that they use (#370)."""
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parent.parent
FILES = re.search(r"FILES: '(.+)'", (ROOT / ".github/workflows/ci.yml").read_text()).group(1)


def test_each_mc_test_file_starts_the_mc_job():
    mc = [p for p in sorted((ROOT / "tests").glob("test_*.py")) if re.search(r"pytest\.mark\.mc\b", p.read_text())]
    assert mc
    missed = [p.name for p in mc if not re.search(FILES, f"tests/{p.name}")]
    assert not missed, f"add these to FILES in .github/workflows/ci.yml: {missed}"


def test_code_starts_the_mc_job_and_docs_do_not():
    for f in ("aoe2mc.py", "buildings.py", "units.py", "game/run.py", "tools/mc_check.py", "requirements.txt"):
        assert re.search(FILES, f), f
    for f in ("docs/LEARNINGS.md", ".claude/skills/autopilot/SKILL.md", "tools/dashboard.py", "tests/test_usage.py"):
        assert not re.search(FILES, f), f
