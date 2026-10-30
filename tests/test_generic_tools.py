"""The generic files of framework/docs/SYSTEM.md use only generic tools (#1963): the bootstrap copies only the generic rows, so a
generic file that runs a specific `tools/X.py` breaks in a new project. And `framework/tools/report.py` works without the
specific `tools/release.py`."""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))

import bootstrap  # noqa: E402
import report  # noqa: E402

TOOL = re.compile(r"tools/[\w/]+\.py")
# (generic file, specific tool): the generic file works without the tool, or names it as text of this project
OPTIONAL = {(".claude/skills/autopilot/owner.md", "tools/mc_shot.py"),       # an example of a check (#1900)
            (".claude/skills/autopilot/report.md", "tools/release.py"),      # report.py skips it (#1963)
            (".claude/skills/ticket/SKILL.md", "tools/replay_drift.py"),     # the lesson of #829
            ("framework/tools/report.py", "tools/release.py"),
            ("framework/tools/usage.py", "tools/release.py")}                          # release_percent() gives None


def specific_tools(rows, read):
    """(generic file, tool) for each existing `tools/X.py` that a generic file names and that is not a generic row.
    Not the tests (their data names tools) and not framework/docs/SYSTEM.md (it describes the specific files too)."""
    generic = {p for p, k in rows if k == "generic"}
    return sorted({(p, t) for p in generic if not p.startswith(("tests/", "framework/tests/")) and p != "framework/docs/SYSTEM.md"
                   for t in TOOL.findall(read(p)) if t not in generic and os.path.exists(os.path.join(ROOT, t))})


def test_no_generic_file_needs_a_specific_tool():
    rows = bootstrap.rows()
    assert set(specific_tools(rows, lambda p: open(os.path.join(ROOT, p)).read())) - OPTIONAL == set()


def test_a_specific_tool_in_a_generic_file_fails():
    rows = [("x.md", "generic"), ("framework/tools/report.py", "generic"), ("tools/release.py", "specific")]
    text = "Run `python3 tools/release.py`, then `framework/tools/report.py` and `tools/nothing.py`."
    assert specific_tools(rows, lambda p: text * (p == "x.md")) == [("x.md", "tools/release.py")]


def test_the_report_has_no_release_bar_without_the_tool(monkeypatch):
    assert report.tool("no_such_tool.py") == ""
    monkeypatch.setattr(report, "tool", lambda *a: {"release.py": "", "tokens.py": "Tokens: 1M eq"}[a[0]])
    body = report.report("Did #1.", "Usage: now", ["Metrics: ticket #1"])
    assert body.startswith("Did #1.\n\nUsage: now\nMetrics: ticket #1\nTokens: 1M eq")
