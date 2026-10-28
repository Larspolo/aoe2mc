"""tools/tokens.py and tools/health.py: the count of the refused force pushes of the runs (#903, #3461)."""
import health
import tokens


def use(tid, cmd):
    return {"type": "assistant", "message": {"id": tid, "content": [
        {"type": "tool_use", "id": tid, "name": "Bash", "input": {"command": cmd}}]}}


def result(tid, text, error=False):
    return {"type": "user", "message": {"content": [
        {"type": "tool_result", "tool_use_id": tid, "content": text, "is_error": error}]}}


def test_a_failed_force_push_counts_and_other_pushes_do_not():
    records = [use("a", "git push --force origin HEAD:b"), result("a", "! [remote rejected] HEAD -> b (denied)"),
               use("b", "git push -f origin b"), result("b", "", error=True),
               use("c", "git push --force-with-lease origin b"), result("c", "+ 1a2b...3c4d b -> b (forced update)"),
               use("d", "git push origin b"), result("d", "! [rejected] b -> b (non-fast-forward)"),
               use("e", "git push -u origin b && git log -f x"), result("e", "denied"),
               use("f", "cat > m.txt <<'EOF'\ngit push --force\nEOF"), result("f", "rejected")]
    assert tokens.refused_pushes(records) == 2


def test_the_force_field_of_the_tokens_line_goes_into_health():
    t = {"eq": 1e6, "calls": 3, "write": 0, "read": 0, "out": 0, "peak": 0, "base": 0, "sinks": {"base": 1e6}}
    line = tokens.line(t, checks={"pytest": [2.0, 1]}, force=2)
    assert " · verify pytest 2.0m 1x · force 2 · sinks base 100%" in line
    comments = [{"body": line}, {"body": tokens.line(t, checks={})}, {"body": tokens.line(t, force=1)}]
    assert health.refused_pushes(comments) == (3, 2)
    assert health.verify_minutes(comments) == {"pytest": (2.0, 1)}
