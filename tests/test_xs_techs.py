"""The technology functions of an XS script (game/xs_host.py, #5840): each one reads or changes the fake side."""
from AoE2ScenarioParser.datasets.techs import TechInfo

import aoe2mc
from game import xs_host
from tests.test_xs_host import ARCHER, side, value

NAMES = aoe2mc.tech_names()
LOOM, BOW = TechInfo.LOOM.ID, TechInfo.BOW_SAW.ID


def program(g):
    g.trigger_menus, g.repeats, g.upgraded = {}, {}, {}
    return g


def test_tech_state():
    g = program(side())
    g.queues = {(0, 0): [{"name": NAMES[TechInfo.DOUBLE_BIT_AXE.ID]}, {"name": NAMES[BOW]}]}
    assert value(g, f"xsGetTechState({LOOM}, 1)") == xs_host.DONE
    assert value(g, f"xsGetTechState({TechInfo.DOUBLE_BIT_AXE.ID}, 1)") == xs_host.RESEARCHING
    assert value(g, f"xsGetTechState({BOW}, 1)") == xs_host.QUEUED
    assert value(g, "xsGetTechState(99999, 1)") == xs_host.INVALID


def test_research_technology(monkeypatch):
    g = program(side())
    got = []
    import train
    monkeypatch.setattr(train, "research", lambda x, e, start=False: got.append((x.player, e["name"], start)))
    assert value(g, f"xsResearchTechnology({LOOM}, true, false, 1)", "bool") is False      # done already
    assert value(g, f"xsResearchTechnology({BOW}, true, false, 1)", "bool") is True
    assert got == [(1, NAMES[BOW], True)]


def test_tech_names():
    g = program(side())
    assert value(g, f'xsGetTechName({LOOM}, 1, true)', "string") == "LOOM"
    assert value(g, f'xsGetTechName({LOOM}, 1)', "string")
    value(g, f'0; xsSetTechName({LOOM}, 1, "Strong")')
    assert g.trigger_names == {NAMES[LOOM]: "Strong"}
    assert value(g, f'xsGetTechName({LOOM}, 1)', "string") == "Strong"


def test_effect_amount_resources_and_objects():
    g = program(side())
    value(g, "0; xsEffectAmount(1, 0, 1, 50, 1)")              # cModResource food add
    value(g, "0; xsEffectAmount(1, 1, 0, 10, 1)")              # cModResource wood set
    value(g, "0; xsEffectAmount(6, 3, 0, 1.5, 1)")             # cMulResource gold
    assert (g.stock["food"], g.stock["wood"], g.stock["gold"]) == (250, 10, 150)
    value(g, f"0; xsEffectAmount(2, {ARCHER}, 0, 0, 1)")       # cEnableObject: disable
    assert g.trigger_menus == {"ARCHER": False}
    assert value(g, f"xsIsObjectAvailable({ARCHER}, 1)", "bool") is False


def test_unit_attribute_effect_warns(capsys):
    value(program(side()), "0; xsEffectAmount(0, 4, 0, 10, 1)")
    assert capsys.readouterr().err.splitlines() == ["XS script: unknown effect 0: skipped"]
