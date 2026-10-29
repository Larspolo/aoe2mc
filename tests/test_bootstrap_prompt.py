"""The bootstrap prints the exact prompt of the autopilot task, and --github accepts a label that exists (#1899)."""
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))

import bootstrap  # noqa: E402


def test_the_bootstrap_prints_the_prompt_of_the_new_project(tmp_path, capsys):
    bootstrap.main([str(tmp_path), "--repo", "me/demo", "--branch", "trunk"])
    out = capsys.readouterr().out
    prompt = out.split('The prompt of the scheduled task "demo autopilot" (step 4), to paste as it is:\n\n', 1)[1]
    assert prompt.split("\n\n")[0] == "/scheduled max"      # the rules are in git: .claude/skills/scheduled (2026-10-29)
    assert (tmp_path / ".claude/skills/scheduled/SKILL.md").exists()
    assert "Larspolo" not in prompt and "aoe2mc" not in prompt and "{" not in prompt
    assert "Merge the first PR of the bootstrap by hand" in out


def test_a_label_that_exists_is_ok():
    call = ["gh", "api", "repos/me/demo/labels", "-f", "name=bug"]
    exists = subprocess.CompletedProcess(call, 1, '{"errors":[{"resource":"Label","code":"already_exists"}]}',
                                         "gh: Validation Failed (HTTP 422)")
    assert bootstrap.label_result(call, exists) == "ok  gh api repos/me/demo/labels"
    other = subprocess.CompletedProcess(call, 1, "", "gh: Not Found (HTTP 404)")
    assert bootstrap.label_result(call, other).startswith("FAIL gh api repos/me/demo/labels: gh: Not Found")
    issue = ["gh", "api", "repos/me/demo/issues"]
    assert bootstrap.label_result(issue, subprocess.CompletedProcess(issue, 1, "already_exists", "x")).startswith("FAIL")
    assert bootstrap.label_result(issue, subprocess.CompletedProcess(issue, 0, "", "")) == "ok  gh api repos/me/demo/issues"
