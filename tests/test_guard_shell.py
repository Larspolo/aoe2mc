"""The PreToolUse hook guard-shell.sh blocks the shell pitfalls of docs/LEARNINGS.md, and nothing else."""
import json
import os
import subprocess

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HOOK = os.path.join(ROOT, ".claude", "hooks", "guard-shell.sh")


def run(command, cwd=ROOT):
    env = {k: v for k, v in os.environ.items() if k not in ("SCRATCH", "OUT")}
    return subprocess.run([HOOK], input=json.dumps({"tool_input": {"command": command}, "cwd": cwd}),
                          capture_output=True, text=True, env=env).returncode


@pytest.mark.parametrize("command", [
    "cat > tests/conftest.py <<'EOF'\nx = 1\nEOF",
    "ls tests/conftest.py 2>&1; cat >tests/conftest.py <<EOF\nx\nEOF",
    "cat > $SCRATCH/x.py <<'EOF'\nprint(1)\nEOF",
    'python3 x.py > "${OUT}/a.txt"',
    "pkill -f server.jar",
    "pgrep -f 'java -Xmx2G' | xargs kill",
    "gh api repos/a/b/issues/1/comments -F body=@- <<EOF\nRun `ruff check .` first.\nEOF",
    "S=/tmp/s && mkdir -p $S & python3 x.py > $S/out.txt",
    "gh api repos/a/b/issues -f title=x -f body=@t.md",
    'gh api repos/a/b/issues -f "body=@t.md"',
    "gh api repos/a/b/issues --raw-field body=@t.md",
])
def test_blocks(command):
    assert run(command) == 2, command


@pytest.mark.parametrize("command", [
    "cat > out/new_file.py <<'EOF'\nx\nEOF",
    "cat >| tests/conftest.py <<'EOF'\nx\nEOF",
    "cat tests/conftest.py > out/copy.py",
    "S=/tmp/s; mkdir -p $S; cat > $S/x.py <<'EOF'\nx\nEOF",
    "for d in a b; do echo 1 > $d/x; done",
    "echo hi > $HOME/x 2>/dev/null",
    "cat > $TMPDIR/x.py <<'EOF'\nx\nEOF",
    "pkill -f '[s]erver.jar'",
    "pgrep -f 'java -Xmx2G' | head",
    "git stash list",
    "git stash",
    "echo 'pkill -f server.jar' | grep pkill",
    "cat > out/t.py <<'EOF'\ncat > tests/conftest.py <<X\npkill -f java\nEOF",
    "gh api x -F body=@- <<'EOF'\nRun `ruff check .` first.\nEOF",
    "python3 - <<EOF\nprint($N)\nEOF",
    "cat <<< `date`",
    "S=/tmp/s; python3 a.py > $S/a 2>&1 & python3 b.py > $S/b",
    "python3 a.py 2>&1 & S=/tmp/s; echo $S",
    "git checkout --ours docs/coverage.md",
    "gh api repos/a/b/issues -f title=x -F body=@t.md",
])
def test_allows(command):
    assert run(command) == 0, command


def test_blocks_a_stash_and_ours_in_a_merge(tmp_path):
    def git(*a):
        subprocess.run(["git", "-C", str(tmp_path), "-c", "user.name=t", "-c", "user.email=t@t", *a], check=True,
                       capture_output=True)
    git("init", "-q")
    git("commit", "-q", "--allow-empty", "-m", "a")
    assert run("git stash", cwd=str(tmp_path)) == 0
    open(os.path.join(tmp_path, ".git", "MERGE_HEAD"), "w").write("0" * 40 + "\n")
    assert run("git stash", cwd=str(tmp_path)) == 2
    assert run("git stash list", cwd=str(tmp_path)) == 0
    assert run("git checkout --ours a.py", cwd=str(tmp_path)) == 2
    assert run("git checkout --theirs docs/coverage.md", cwd=str(tmp_path)) == 0
