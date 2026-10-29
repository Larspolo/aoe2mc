"""The SessionStart hook in one environment of two projects (#1964): with the version file of another project and no
own one, the hook asks for a new setup script only when a need of SETUP_NEEDS is missing."""
import os
import subprocess

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HOOK = os.path.join(ROOT, ".claude", "hooks", "session-start.sh")


def run(tmp_path, needs, version=None):
    """The output of the version check of the hook in tmp_path: a setup script of version 7 with needs, and the
    version file of this project with version (None: no file)."""
    check = open(HOOK).read().split("# The environment runs", 1)[1]
    etc = tmp_path / "etc"
    etc.mkdir(exist_ok=True)
    if version is not None:
        (etc / "aoe2mc-setup-version").write_text(f"{version}\n")
    (tmp_path / "scripts").mkdir(exist_ok=True)
    (tmp_path / "scripts" / "cloud-setup.sh").write_text(f'SETUP_VERSION=7   # x\nSETUP_NEEDS="{needs}"\n')
    script = "set -euo pipefail\n#" + check.replace("/etc/", f"{etc}/")
    out = subprocess.run(["bash", "-c", script], cwd=tmp_path, capture_output=True, text=True, timeout=30)
    assert out.returncode == 0, out.stderr
    return out.stdout


def test_another_project_whose_script_installs_the_needs_gives_no_message(tmp_path):
    (tmp_path / "tool.json").write_text("{}")
    assert run(tmp_path, f"bash {tmp_path}/tool*.json") == ""
    assert run(tmp_path, "") == ""                                     # a project with no needs


def test_a_missing_need_or_an_old_own_version_gives_the_message(tmp_path):
    out = run(tmp_path, "bash no-such-command-1964")
    assert "version none" in out and "is version 7" in out and "missing: no-such-command-1964" in out
    out = run(tmp_path, "bash", version=6)                            # the own script is old
    assert "version 6" in out and "(missing: none)" in out
    assert run(tmp_path, "no-such-command-1964", version=7) == ""     # the own script is new
