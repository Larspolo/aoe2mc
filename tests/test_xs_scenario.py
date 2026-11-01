"""The converter keeps the XS code of a scenario in aoe2mc.json (#5122): the Script Call conditions and effects
(the list "xs") and the map script of --xs FILE ("xs_script"). Without the file, a script name gives a warning."""
import contextlib
import io
import json

from AoE2ScenarioParser.scenarios.aoe2_de_scenario import AoE2DEScenario

import aoe2mc
from tools import scenarios


def world(tmp_path, xs=None, name=""):
    with contextlib.redirect_stdout(io.StringIO()):
        scn = AoE2DEScenario.from_file(scenarios.tiny(str(tmp_path / "t.aoe2scenario")))
        scn.xs_manager.script_name = name
        scn.xs_manager.xs_check.enabled = False          # the xs-check program of the parser: not here
        t = scn.trigger_manager.add_trigger("Call")
        t.new_condition.script_call(xs_function="bool c() { return (true); }")
        t.new_effect.script_call(message="main();")
        src = scenarios.save(scn, str(tmp_path / "x.aoe2scenario"))
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        aoe2mc.convert(src, str(tmp_path / "W"), xs=xs)
    with open(tmp_path / "W" / "aoe2mc.json") as f:
        return json.load(f), out.getvalue(), t.trigger_id


def test_the_world_keeps_the_xs_code_of_each_trigger(tmp_path):
    data, out, tid = world(tmp_path)
    assert {"trigger": tid, "kind": "condition", "code": "bool c() { return (true); }"} in data["xs"]
    assert {"trigger": tid, "kind": "effect", "code": "main();"} in data["xs"]
    assert "xs_script" not in data and "warning" not in out


def test_a_script_name_without_a_file_gives_one_warning(tmp_path):
    _, out, _ = world(tmp_path, name="my_script")
    assert [line for line in out.splitlines() if "warning" in line and "my_script" in line] != []
    assert out.count("my_script") == 1


def test_the_xs_file_goes_into_the_world(tmp_path):
    xs = tmp_path / "my_script.xs"
    xs.write_text("void main() { }\n")
    data, out, _ = world(tmp_path, xs=str(xs), name="my_script")
    assert data["xs_script"] == ["my_script", "void main() { }\n"] and "warning" not in out


def test_the_xs_option_reaches_convert(monkeypatch):
    seen = {}
    monkeypatch.setattr(aoe2mc, "convert", lambda *a, **kw: seen.update(kw))
    aoe2mc.main(["in.aoe2scenario", "OUT", "--xs", "f.xs"])
    assert seen["xs"] == "f.xs"
