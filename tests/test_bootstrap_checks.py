"""The starts of the bootstrap make CI, the SessionStart hook and the verify skill work in a new repository (#1897):
lint and the fast tests pass right after the bootstrap, also the copied tests of the generic tools (#1900)."""
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))

import bootstrap  # noqa: E402


def test_lint_and_fast_tests_pass_after_the_bootstrap(tmp_path):
    bootstrap.bootstrap(str(tmp_path), "me/demo")
    for cmd in (["git", "init", "-q"], ["git", "add", "-A"]):       # test_agent_config.py greps the git files
        subprocess.run(cmd, cwd=tmp_path, check=True)
    for cmd in ([sys.executable, "-m", "ruff", "check", "."], [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider"]):
        r = subprocess.run(cmd, cwd=tmp_path, capture_output=True, text=True, timeout=120)
        assert r.returncode == 0, (cmd, r.stdout[-2000:], r.stderr[-2000:],
                                   "the copy has only the generic tools: a generic tool must import a project tool "
                                   "inside its try (#3560)")


def test_the_starts_have_what_the_hook_and_ci_read(tmp_path):
    bootstrap.bootstrap(str(tmp_path), "me/demo")
    setup = (tmp_path / "scripts/cloud-setup.sh").read_text()
    assert "\nSETUP_VERSION=1 " in setup and "/etc/demo-setup-version" in setup and os.access(tmp_path / "scripts/cloud-setup.sh", os.X_OK)
    assert (tmp_path / ".claude/hooks/session-start.sh").read_text().count("/etc/demo-setup-version") == 1
    assert {"numpy", "pytest", "ruff"} <= {line.split()[0] for line in (tmp_path / "requirements-dev.txt").read_text().splitlines()}
    verify = (tmp_path / ".claude/skills/verify/SKILL.md").read_text()
    assert verify.startswith("---\nname: verify\n") and "ruff check ." in verify and "python3 -m pytest" in verify
