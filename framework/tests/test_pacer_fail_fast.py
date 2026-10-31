"""A failed cycle ends a run that a person started at once (owner: the result of a try after a fix shows at once).
The loop run (github-actions[bot]) and the cron still wait one cycle, then start the next run: no fast loop of red runs."""
from test_pacer_restart import calls, loop, repo  # noqa: F401  (repo is a fixture)


def failing_cycle(bin_, log):
    """A python3 whose switch says "workflow" and whose cycle (`--log`) fails, as on a broken secret."""
    f = bin_ / "python3"
    f.write_text(f'#!/bin/sh\necho "python3 $*" >> {log}\ncase "$*" in (*--switch*) exit 0;; (*) exit 1;; esac\n')
    f.chmod(0o755)


def test_a_failed_cycle_of_a_person_ends_at_once_with_no_sleep_and_no_next_run(repo, tmp_path, monkeypatch):  # noqa: F811  (repo is a fixture)
    run, other, bin_, log = repo
    failing_cycle(bin_, log)
    monkeypatch.setenv("GITHUB_EVENT_NAME", "workflow_dispatch")
    monkeypatch.setenv("GITHUB_ACTOR", "a-person")
    r = loop(run, bin_, tmp_path)
    assert r.returncode == 1, r.stderr
    assert not any(c.startswith(("sleep", "gh workflow run pacer.yml")) for c in calls(log))


def test_a_failed_cycle_of_the_loop_waits_and_starts_the_next_run(repo, tmp_path, monkeypatch):  # noqa: F811  (repo is a fixture)
    run, other, bin_, log = repo
    failing_cycle(bin_, log)
    monkeypatch.setenv("GITHUB_EVENT_NAME", "workflow_dispatch")
    monkeypatch.setenv("GITHUB_ACTOR", "github-actions[bot]")
    r = loop(run, bin_, tmp_path)
    assert r.returncode == 1, r.stderr
    assert "sleep 600" in calls(log)
    assert "gh workflow run pacer.yml --repo o/r --ref main" in calls(log)


def test_a_failed_cycle_of_the_cron_waits_and_starts_the_next_run(repo, tmp_path, monkeypatch):  # noqa: F811  (repo is a fixture)
    run, other, bin_, log = repo
    failing_cycle(bin_, log)
    monkeypatch.setenv("GITHUB_EVENT_NAME", "schedule")
    monkeypatch.setenv("GITHUB_ACTOR", "a-person")
    r = loop(run, bin_, tmp_path)
    assert r.returncode == 1, r.stderr
    assert "sleep 600" in calls(log)
    assert "gh workflow run pacer.yml --repo o/r --ref main" in calls(log)
