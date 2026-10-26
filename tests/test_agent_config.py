"""The project values of the agent system come from agent.toml (#905)."""
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))

import agent_config  # noqa: E402

FAKE = """repo = "someone/other"
owner = "someone"
branch = "trunk"
[status]
issue = 7
label = "bot-status"
paused = "stop"
[commands]
lint = "flake8"
[docs]
learnings = "NOTES.md"
"""


def test_the_default_config_holds_the_project_values():
    c = agent_config.CONFIG
    assert c["repo"] == "Larspolo/aoe2mc" and c["owner"] == "Larspolo" and c["branch"] == "main"
    assert c["status"] == {"issue": 1, "label": "agent-status", "paused": "paused"}
    assert set(c["commands"]) >= {"lint", "fast", "slow", "server"}
    assert all(os.path.exists(os.path.join(ROOT, p)) for p in c["docs"].values())


def test_the_tools_read_another_config(tmp_path):
    (tmp_path / "agent.toml").write_text(FAKE)
    env = {k: v for k, v in os.environ.items() if k != "GITHUB_REPOSITORY"}
    env["AGENT_CONFIG"] = str(tmp_path / "agent.toml")
    code = ("import inspect, claim, dashboard, health, refimage;"
            "print(dashboard.REPO, dashboard.STATUS, dashboard.PAUSED, sorted(dashboard.SKIP), claim.STATUS,"
            " health.OWNER, health.STATUS, inspect.signature(claim.revived), refimage.HEADERS['User-Agent'])")
    out = subprocess.run([sys.executable, "-c", code], cwd=os.path.join(ROOT, "tools"), env=env,
                         capture_output=True, text=True, check=True).stdout.split()
    assert out[:3] == ["someone/other", "bot-status", "stop"]
    assert "'bot-status'," in out and "'agent-status'," not in " ".join(out)
    assert "7" in out and "someone" in out
    assert "(path='NOTES.md', base='origin/trunk')" in " ".join(out)
    assert out[-1] == "(https://github.com/someone/other)"


def test_no_tool_skill_or_workflow_names_the_repository():
    """Only agent.toml names it, and .claude/settings.json: permission rules cannot read a file. The copy of the
    owner's dashboard page (tools/dashboard_artifact, #982) is data of this project, not a tool."""
    found = subprocess.run(["git", "grep", "-l", "Larspolo/aoe2mc", "--", ".claude", "tools", ".github",
                            ":!tools/dashboard_artifact"],
                           cwd=ROOT, capture_output=True, text=True).stdout.split()
    assert found == [".claude/settings.json"]
