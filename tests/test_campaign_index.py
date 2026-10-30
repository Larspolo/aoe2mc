"""campaign.json: the index of a converted campaign, the order of its scenarios for the game program (#3504)."""
import contextlib
import io
import json

import pytest
import scenarios
from test_campaign import campaign

import aoe2mc


@pytest.fixture(scope="module")
def two(tmp_path_factory):
    d = tmp_path_factory.mktemp("index")
    s1 = scenarios.tiny(str(d / "a.aoe2scenario"))
    s2 = scenarios.save(scenarios.new_scenario(8), str(d / "b.aoe2scenario"))
    return campaign(d / "c.aoe2campaign", [s1, s2], name="Index test")


def run(*args):
    with contextlib.redirect_stdout(io.StringIO()):
        aoe2mc.main([str(a) for a in args])


def test_index_lists_the_scenarios_in_order(two, tmp_path):
    run(two, tmp_path / "out")
    index = json.loads((tmp_path / "out" / "campaign.json").read_text(encoding="utf-8"))
    assert index == {"name": "Index test", "scenarios": [
        {"number": 1, "name": "S1", "world": "1 S1"},
        {"number": 2, "name": "S2", "world": "2 S2"}]}
    for entry in index["scenarios"]:
        assert (tmp_path / "out" / entry["world"] / "level.dat").is_file()


def test_index_marks_the_scenario_that_is_not_converted(two, tmp_path):
    run(two, tmp_path / "out", "--scenario", 2)
    index = json.loads((tmp_path / "out" / "campaign.json").read_text(encoding="utf-8"))
    assert [e.get("converted") for e in index["scenarios"]] == [False, None]
    assert (tmp_path / "out" / "2 S2" / "level.dat").is_file()
