"""tools/refimage.py names the repository of agent.toml in its User-Agent (#905). A project tool: its test is not in
the generic test_agent_config.py (#1900)."""
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def test_refimage_reads_another_config(tmp_path):
    (tmp_path / "agent.toml").write_text('repo = "someone/other"\nowner = "someone"\nbranch = "trunk"\n')
    env = {k: v for k, v in os.environ.items() if k != "GITHUB_REPOSITORY"}
    env["AGENT_CONFIG"] = str(tmp_path / "agent.toml")
    out = subprocess.run([sys.executable, "-c", "import refimage; print(refimage.HEADERS['User-Agent'])"],
                         cwd=os.path.join(ROOT, "tools"), env=env, capture_output=True, text=True, check=True).stdout
    assert out.split()[-1] == "(https://github.com/someone/other)"
