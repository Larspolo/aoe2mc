"""Fewer calls at the start of a run (2026-10-29): `report.py` measures the setup minutes in the transcript (no
`date` call), `cycle_start.py` prints the values of `agent.toml` and the time (no `cat agent.toml`), and `--lane`
sets the lane of the run (no `git config` call)."""
import datetime
import subprocess

import cycle_start
import dashboard
import report
import tokens
from agent_config import CONFIG


def at(seconds):
    return f"2026-10-29T12:{seconds // 60:02d}:{seconds % 60:02d}.000Z"


def call(seconds, uid, command):
    return {"type": "assistant", "timestamp": at(seconds),
            "message": {"id": uid, "usage": {"input_tokens": 10},
                        "content": [{"type": "tool_use", "id": uid, "name": "Bash", "input": {"command": command}}]}}


def test_the_setup_is_the_time_from_the_start_to_the_first_won_claim():
    recs = [{"type": "user", "timestamp": at(0)}, call(30, "a", "python3 tools/cycle_start.py"),
            call(90, "b", "python3 tools/claim.py 7 --or 8"),
            {"type": "user", "timestamp": at(95), "message": {"content": [
                {"type": "tool_result", "tool_use_id": "b", "content": "#7 owned by another run\nclaimed claim/8"}]}}]
    assert tokens.run_data(recs)["setup"] == 1.5
    assert tokens.run_data(recs[:3])["setup"] is None                   # no claim won


def test_the_report_takes_the_measured_setup_for_the_first_ticket(monkeypatch):
    monkeypatch.setattr(report, "numbers", lambda: {"setup": 7.4})
    monkeypatch.setattr(report, "measured", lambda: {})
    monkeypatch.setattr(report, "report", lambda text, usage, lines: "\n".join(lines))
    printed = []
    monkeypatch.setattr("builtins.print", printed.append)
    args = ["--text", "t", "--usage", "u", "--ticket", "7", "--size", "S", "--result", "pr #1",
            "--ticket", "8", "--size", "S", "--result", "closed"]
    report.main(args)
    first, second = printed[0].splitlines()
    assert "· setup 7 min ·" in first and "· setup 0 min ·" in second and "· closed ·" in second
    report.main(args + ["--setup", "3"])
    assert "· setup 3 min ·" in printed[1].splitlines()[0]                # a given --setup wins


def test_the_status_line_names_the_time_and_the_project_values():
    now = datetime.datetime(2026, 10, 29, 15, 4, 5, tzinfo=datetime.timezone.utc)
    line = cycle_start.status_line(1, {"last_run": "x", "runs": 9}, now, "haiku")
    assert line == (f"#1 · last run x · runs 9 · now 2026-10-29T15:04:05Z · repo {CONFIG['repo']} · owner "
                    f"{CONFIG['owner']} · branch {CONFIG['branch']} · lane haiku (git config aoe2mc.lane)")


def test_a_lane_run_sets_its_lane_at_the_start(monkeypatch):
    calls = []
    monkeypatch.setattr(subprocess, "run", lambda cmd, **k: calls.append(cmd) or subprocess.CompletedProcess(cmd, 0, ""))
    status = {"number": 1, "labels": [{"name": CONFIG["status"]["label"]}, {"name": CONFIG["status"]["paused"]}]}
    monkeypatch.setattr(dashboard, "pages", lambda path, limit=10: [status])
    assert cycle_start.main(["--lane", "haiku"]) == 3                   # paused: it stops after the lane
    assert ["git", "config", "aoe2mc.lane", "haiku"] in calls
