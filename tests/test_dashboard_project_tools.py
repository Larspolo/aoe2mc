"""dashboard.py finds the project tool dashboard_data.py when it runs from framework/tools (#5804)."""
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS = os.path.join(ROOT, "framework", "tools")


def test_dashboard_imports_project_tool_from_framework_tools():
    # a child process: the test process keeps its own sys.path
    code = "import dashboard; import dashboard_data; print(callable(dashboard_data.releases))"
    out = subprocess.run([sys.executable, "-c", code], cwd=TOOLS, capture_output=True, text=True)
    assert out.returncode == 0, out.stderr
    assert out.stdout.strip() == "True"
