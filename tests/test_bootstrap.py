"""The bootstrap sets up the agent system in a new repository (#906)."""
import os
import sys

import tomllib

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))

import bootstrap  # noqa: E402


def files(d):
    return sorted(os.path.relpath(os.path.join(p, f), d) for p, _, fs in os.walk(d) for f in fs)


def test_table_names_real_files():
    rows = bootstrap.rows()
    assert len(rows) > 20 and ("framework/tools/claim.py", "generic") in rows and ("CLAUDE.md", "specific") in rows
    assert [p for p, _ in rows if not os.path.exists(os.path.join(ROOT, p))] == []


def test_bootstrap_writes_generic_files_and_config(tmp_path, capsys):
    bootstrap.main([str(tmp_path), "--repo", "me/demo"])
    out = capsys.readouterr().out
    got = files(tmp_path)
    rows = dict(bootstrap.rows())
    assert {p for p, k in rows.items() if k == "generic"} <= set(got)
    assert set(got) - {p for p, k in rows.items() if k == "generic"} == set(bootstrap.STUBS)
    # no file of the converter, the game program, their docs and tests
    assert not [p for p in got if p.startswith(("game/", "tests/", "datapacks/", "docs/research/")) and p not in bootstrap.STUBS
                and rows.get(p) != "generic"
                or p in ("aoe2mc.py", "buildings.py", "units.py", "scx.py", "docs/DESIGN.md")]
    cfg = tomllib.load(open(tmp_path / "agent.toml", "rb"))
    assert (cfg["repo"], cfg["owner"], cfg["branch"], cfg["status"]["label"]) == ("me/demo", "me", "main", "agent-status")
    for p in got:
        text = open(tmp_path / p, errors="replace").read()
        assert "Larspolo" not in text and "aoe2mc" not in text, p
    assert "Repository `me/demo`" in out and "Setup steps of the owner" in out and "- .claude/skills/verify/SKILL.md" not in out


def test_github_calls_make_labels_and_status_issue():
    calls = bootstrap.github_calls("me/demo", "# name|color|description\nP0|b60205|Do next\nbug|d73a4a|A bug\n")
    assert [c[2] for c in calls] == ["repos/me/demo/labels"] * 2 + ["repos/me/demo/issues"]
    assert "name=P0" in calls[0] and "labels[]=agent-status" in calls[-1]
    assert any(a.startswith("body=<!-- agent-state:") for a in calls[-1])
