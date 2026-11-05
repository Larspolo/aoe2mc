"""DE base scenarios of format 1.36 and a later file in the same process (#5830). AoE2ScenarioParser disables a
field that the format does not have (script_name: since 1.40) on the class, so the field stayed disabled for all later
files. The test makes the parser see format 1.36 for one read: the same path as a real 1.36 file."""
import contextlib
import io

import pytest
from AoE2ScenarioParser.scenarios.aoe2_de_scenario import AoE2DEScenario
from AoE2ScenarioParser.scenarios.scenario_store import getters

import aoe2mc
from tools import scenarios


@pytest.fixture
def named(tmp_path):
    """A tiny scenario with the XS script name "my_script"."""
    with contextlib.redirect_stdout(io.StringIO()):
        scn = AoE2DEScenario.from_file(scenarios.tiny(str(tmp_path / "t.aoe2scenario")))
        scn.xs_manager.script_name = "my_script"
        return scenarios.save(scn, str(tmp_path / "n.aoe2scenario"))


def read_as_136(path, monkeypatch):
    with monkeypatch.context() as m:
        m.setattr(getters, "get_scenario_version", lambda uuid: "1.36")
        return aoe2mc.read_scenario(path)


def test_a_136_file_without_a_script_name_reads(named, monkeypatch):
    try:
        assert read_as_136(named, monkeypatch)[4]["xs_name"] == ""
    finally:
        aoe2mc.reset_parser_links()          # the other tests of this process get the parser as it was


def test_a_later_file_after_a_136_file_keeps_its_fields(named, monkeypatch):
    try:
        read_as_136(named, monkeypatch)
        assert aoe2mc.read_scenario(named)[4]["xs_name"] == "my_script"
    finally:
        aoe2mc.reset_parser_links()
