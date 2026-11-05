"""The warning line of a "Script Call" without a datapack form prints once per conversion (#5833): the top-level calls of
trigger_files do not clear the warnings again, and a second conversion in the same process prints it once more."""
import contextlib
import io

from AoE2ScenarioParser.scenarios.aoe2_de_scenario import AoE2DEScenario

import aoe2mc
from tools import scenarios

XS = "int a = 1;\nvoid main() {\n  a = sin(a);\n}\n"


def source(tmp_path):
    with contextlib.redirect_stdout(io.StringIO()):
        scn = AoE2DEScenario.from_file(scenarios.tiny(str(tmp_path / "t.aoe2scenario")))
        scn.xs_manager.xs_check.enabled = False
        t = scn.trigger_manager.add_trigger("Call")
        t.new_effect.script_call(message=XS)
        return scenarios.save(scn, str(tmp_path / "x.aoe2scenario"))


def convert_lines(src, out):
    log = io.StringIO()
    with contextlib.redirect_stdout(log):
        aoe2mc.convert(src, str(out))
    return [x for x in log.getvalue().splitlines() if "XS script" in x]


def test_a_warning_prints_once_per_conversion(tmp_path):
    src = source(tmp_path)
    first = convert_lines(src, tmp_path / "W1")
    assert len(first) == 1
    second = convert_lines(src, tmp_path / "W2")
    assert second == first
