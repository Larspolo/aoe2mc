"""game/per.py and game/garrison.py: the airef forms of up-garrison, up-guard-unit, up-retreat-to and
up-set-attack-stance (ObjectId typeOp UnitId, #5179) run with no exception, and a ram holds units (up-ungarrison)."""
import pytest
from test_per_up_unit_orders import army

from game import garrison, per

EXAMPLES = ["(up-garrison battering-ram c: militiaman)", "(up-guard-unit monk c: spearman-line)",
            "(up-retreat-to castle c: knight-line)", "(up-set-attack-stance militiaman c: stance-defensive)",
            "(up-ungarrison c: battering-ram)", "(up-garrison my-unique-unit c: militiaman)"]


@pytest.mark.parametrize("text", EXAMPLES)
def test_airef_examples_run(monkeypatch, text):
    server, b, s, log, tc = army(monkeypatch)
    (rule,) = per.parse(f"(defrule (true) => {text})")
    for a in rule.actions:
        s.act(0, a)


def test_a_ram_holds_militia_and_lets_them_out(monkeypatch):
    server, b, s, log, tc = army(monkeypatch)
    g = b.g
    g.soldiers["r0"] = "BATTERING_RAM"
    server.entities["r0"] = {"Pos": (7.5, 64.0, 6.5), "Rotation": (0.0, 0.0), "Health": 10.0}
    s.act(None, ("up-garrison", "battering-ram", "c:", "militiaman"))
    assert sorted(g.boarding) == ["m0", "m1"]
    garrison.tick(g)                                                   # at the ram: they go in
    assert g.cargo["r0"] == ["m0", "m1"] and not g.boarding and {"m0", "m1"} <= garrison.inside(g)
    s.act(None, ("up-ungarrison", "c:", "battering-ram"))
    assert "r0" not in g.cargo
