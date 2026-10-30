"""`tokens.phase()`: the PR body, the commit message and the comment files count as the report phase (#3231)."""
import tokens


def test_pr_text_files_are_report():
    assert tokens.phase("Bash", {"command": "cat > /s/body.md <<'EOF'\nx\nEOF"}) == "report"
    assert tokens.phase("Bash", {"command": "cat > /s/msg.txt <<'EOF'\nx\nEOF"}) == "report"
    assert tokens.phase("Bash", {"command": "tee /s/Comment_1.md"}) == "report"
    assert tokens.phase("Write", {"file_path": "/s/msg.txt"}) == "report"
    assert tokens.phase("Write", {"file_path": "/s/body.md"}) == "report"


def test_code_files_stay_code():
    assert tokens.phase("Bash", {"command": "cat > tests/test_x.py <<'EOF'\nx\nEOF"}) == "code"
    assert tokens.phase("Write", {"file_path": "tools/x.py"}) == "code"
    assert tokens.phase("Edit", {"file_path": "framework/tools/tokens.py"}) == "code"
