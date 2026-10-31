"""game/per.py: up-set-attack-stance reads the airef stance names (stance-stand-ground, #5097) as well as the ids."""
from test_per_up_unit_orders import army


def test_airef_stance_names_set_the_stance(monkeypatch, capsys):
    server, b, s, log, tc = army(monkeypatch)
    s.act(None, ("up-set-attack-stance", "militiaman", "c:", "stance-stand-ground"))
    assert log.pop() == ("stance", ["m0", "m1"], "stand_ground")
    s.act(None, ("up-set-attack-stance", "militiaman", "c:", "stance-aggressive"))
    assert log.pop() == ("stance", ["m0", "m1"], "aggressive")
    assert "unknown" not in capsys.readouterr().err
