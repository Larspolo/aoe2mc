"""game/per.py: the fact map-type reads the random map script of the world (aoe2mc.json "lobby" "script", #5102)."""
from test_per_setup import script

from game import per


def test_a_random_map_world_has_the_type_of_its_script(capsys):
    s, b = script()
    b.g.data["lobby"] = {"map_size": "tiny", "mode": "standard", "script": "Arabia"}
    assert s.check(("map-type", "arabia")) and not s.check(("map-type", "arena"))
    assert not s.check(("map-type", "scenario-map"))
    assert "map-type" not in capsys.readouterr().err


def test_a_scenario_world_is_a_scenario_map(capsys):
    s, b = script()
    assert s.check(("map-type", "scenario-map")) and not s.check(("map-type", "arabia"))
    assert "map-type" not in capsys.readouterr().err


def test_a_script_name_takes_the_airef_form():
    assert per.map_type({"lobby": {"script": "Black_Forest"}}) == "black-forest"
    assert per.map_type({}) == "scenario-map"


def test_an_unknown_map_type_warns_once(capsys):
    s, b = script()
    assert not s.check(("map-type", "no-such-map")) and not s.check(("map-type", "no-such-map"))
    assert capsys.readouterr().err.count("unknown map-type no-such-map") == 1
