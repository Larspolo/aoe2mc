"""#5825: research_list compiles the triggers once. Each trigger_files call runs the whole fixed point and prints the
XS warnings again, so one call for 10 triggers must give the same list as before, with one call of trigger_files."""
from test_scenario_research import research
from test_trigger_objects import trig

import aoe2mc


def test_research_list_calls_trigger_files_once_and_gives_the_same_list(monkeypatch):
    triggers = [trig([research("LOOM", player=i % 2 + 1)], id=10 + i) for i in range(10)]
    calls = []
    real = aoe2mc.trigger_files

    def spy(*args, **kwargs):
        calls.append(1)
        return real(*args, **kwargs)

    monkeypatch.setattr(aoe2mc, "trigger_files", spy)
    got = aoe2mc.research_list(triggers)
    assert len(calls) == 1
    assert got == [dict(score=f"#r{10 + i}.0", player=i % 2 + 1, technology="LOOM") for i in range(10)]
