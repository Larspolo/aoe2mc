"""#5798: (load "FILE") in the embedded AI script of a scenario loads the AI file that the scenario carries."""
import contextlib
import io
import json

from AoE2ScenarioParser.sections.aoe2_file_section import AoE2FileSection

import aoe2mc
from game import per, run
from tools import scenarios


def test_a_load_takes_the_file_of_the_scenario(capsys):
    consts = {}
    per.parse('(load "AiBuilder\\\\x")', files={"AiBuilder/X.per": "(defconst a 1)"}, consts=consts)
    assert consts["a"] == 1
    assert per.parse('(load "missing")', files={}) == []
    assert "no file missing for load" in capsys.readouterr().err


def test_the_conversion_writes_the_ai_files(tmp_path):
    scn = scenarios.new_scenario(24)
    f = scn.sections["Files"]
    ai = AoE2FileSection.from_model(f.struct_models["AI2Struct"], scn.uuid, set_defaults=True)
    ai.ai_file_name, ai.ai_file = "AiBuilder\\x.per", "(defrule (true) => (train villager))"
    f.ai_files, f.ai_files_present, f.number_of_ai_files = [ai], 1, 1
    p = scn.player_manager.players[2]
    p.personality, p.ai_script = "rusher", '(load "AiBuilder\\x")'
    out = scenarios.save(scn, str(tmp_path / "s.aoe2scenario"))
    with contextlib.redirect_stdout(io.StringIO()):
        aoe2mc.convert(out, str(tmp_path / "W"))
    with open(tmp_path / "W" / "aoe2mc.json") as fp:
        data = json.load(fp)
    assert data["ai_files"] == {"AiBuilder/x.per": ai.ai_file}
    rules = run.bot_script(data["players"], 2, None, 0, ai_files=data["ai_files"])
    assert len(rules) == 1 and rules[0].file == "AiBuilder/x.per"
