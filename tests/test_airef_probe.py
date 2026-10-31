"""tools/airef_probe.py: each example of the AoE2 AI Scripting Encyclopedia runs on a bot; the crashes and the
unknown warnings are printed (#5192)."""
import airef_probe

SAMPLE = r'''cA.example = [ { title: "Good", data: "(defrule (true) => (disable-self))" } ];
cB.example = [ { title: "Unknown fact", data: "(defrule (no-such-fact-xyz) => (disable-self))" } ];
'''


def test_the_probe_prints_the_examples_and_the_unknown_fact(tmp_path, capsys):
    path = tmp_path / "commands.js"
    path.write_text(SAMPLE, encoding="utf-8")
    assert airef_probe.main([str(path)]) == 0                       # no crash: exit 0
    out = capsys.readouterr().out
    assert "examples: 2" in out and "crashes: 0" in out
    assert "unknown fact no-such-fact-xyz: skipped" in out and "[cB]" in out


def test_a_broken_example_is_a_crash_and_exits_1(tmp_path, capsys):
    path = tmp_path / "commands.js"
    path.write_text('cD.example = [ { title: "Broken", data: "(defrule (true) => (disable-self)" } ];\n', encoding="utf-8")
    assert airef_probe.main([str(path)]) == 1
    assert "crashes: 1" in capsys.readouterr().out


def test_a_missing_load_file_is_not_a_crash(tmp_path, capsys):
    path = tmp_path / "commands.js"
    path.write_text('cE.example = [ { title: "Load", data: "(load \\"nofile\\")" } ];\n', encoding="utf-8")
    assert airef_probe.main([str(path)]) == 0
    assert "crashes: 0" in capsys.readouterr().out
