"""tools/release.py as a command: it finds `dashboard` of framework/tools (#4743; the move of #4195 broke the CLI)."""
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def test_release_command_imports_dashboard():
    code = "import runpy, sys; sys.argv = ['release.py']; runpy.run_path('tools/release.py', run_name='x'); import dashboard"
    r = subprocess.run([sys.executable, "-I", "-c", code], cwd=ROOT, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
