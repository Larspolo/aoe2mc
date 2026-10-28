"""The technology triggers use the names of game/data/train.jsonl, not the AoE2ScenarioParser names: the unit upgrades
(CROSSBOWMAN is CROSSBOWMAN_UPGRADE there), BOMBARD_TOWER_TECH and SPIES (data/tech_names.jsonl, the ticket of the
technology names)."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "game"))
import aoe2mc  # noqa: E402
import scenarios  # noqa: E402
import train  # noqa: E402
from AoE2ScenarioParser.datasets.techs import TechInfo  # noqa: E402
from units import rows  # noqa: E402


def read(tmp_path, tech):
    scn = scenarios.new_scenario(24)
    t = scn.trigger_manager.add_trigger("All")
    t.new_condition.research_technology(source_player=1, technology=tech.ID)
    t.new_effect.research_technology(source_player=1, technology=tech.ID)
    path = scenarios.save(scn, str(tmp_path / "tech.aoe2scenario"))
    return aoe2mc.read_scenario(path)[4]["triggers"][0]


def test_a_unit_upgrade_has_the_name_of_the_game_program(tmp_path):
    trig = read(tmp_path, TechInfo.CROSSBOWMAN)
    assert trig["effects"][0]["technology"] == "CROSSBOWMAN_UPGRADE"
    assert trig["conditions"][0]["technology"] == "CROSSBOWMAN_UPGRADE"
    _, files = aoe2mc.trigger_files([trig])                       # the tick function tests the name of the game program
    assert "execute if score #p1.CROSSBOWMAN_UPGRADE aoe_tech matches 1.. unless score #0 aoe_trig matches 1 run " \
           "function aoe2mc:trigger/0" in files["data/aoe2mc/function/tick.mcfunction"].splitlines()


def test_bombard_tower_and_spies_have_the_names_of_the_game_program(tmp_path):
    assert read(tmp_path, TechInfo.BOMBARD_TOWER)["effects"][0]["technology"] == "BOMBARD_TOWER_TECH"
    assert read(tmp_path, TechInfo.SPIES_AND_TREASON)["effects"][0]["technology"] == "SPIES"


def test_a_technology_with_the_same_name_keeps_it(tmp_path):
    assert read(tmp_path, TechInfo.LOOM)["effects"][0]["technology"] == "LOOM"


def test_each_line_names_a_technology_of_both_lists():
    techs = set(train.TECHS)
    for row in rows("tech_names.jsonl"):
        assert row["name"] in techs, row
        assert row["tech"] in {t.name for t in TechInfo}, row


def test_each_technology_of_the_game_program_has_a_trigger_name():
    names = {t.name for t in TechInfo} | {row["name"] for row in rows("tech_names.jsonl")}
    missing = set(train.TECHS) - names
    assert missing <= {"ARCHERY_RANGE_RECRUITMENT_DOCTRINE", "BARRACKS_RECRUITMENT_DOCTRINE",
                       "STABLE_RECRUITMENT_DOCTRINE", "TREASON", "FARM_RESEED"}, missing

