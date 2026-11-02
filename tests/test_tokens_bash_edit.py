"""`tokens.phase()`: a Bash script that writes a file is `code`, also when the write is in a heredoc (#5616)."""
import tokens


def bash(cmd):
    return tokens.phase("Bash", {"command": cmd})


def test_a_python_heredoc_that_writes_a_file_is_code():
    edit = "cd /r && python3 - <<'EOF'\np='aoe2mc.py'\ns=open(p).read()\nopen(p,'w').write(s.replace('a','b'))\nEOF"
    assert bash(edit) == "code"
    assert bash("python3 - <<'EOF'\nfrom pathlib import Path\nPath('x.py').write_text('y')\nEOF") == "code"
    assert bash("python3 - <<'EOF'\nf=open(os.path.join(d, 'x'), \"w\")\nEOF") == "code"


def test_a_heredoc_that_only_reads_stays_read_and_other_rules_win():
    assert bash("python3 - <<'EOF'\nimport json\nprint(json.load(open('a.json')))\nEOF") == "read"
    assert bash("sed -n 1,40p aoe2mc.py") == "read"
    assert bash("python3 framework/tools/report.py --post <<'EOF'\nopen(p,'w')\nEOF") == "report"
    assert bash("python3 -m pytest tests/test_x.py") == "verify"
