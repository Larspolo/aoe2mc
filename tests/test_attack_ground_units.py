"""Each unit of the AoE2 Attack Ground list (combat.GROUND) gets a range with a blast value, which `aoe attackground`
needs (#4207). A packed Trebuchet refuses the order with a hint; an unpacked one shoots."""
from test_attack_ground_order import setup

from game import combat, stance, trebuchet


def test_each_attack_ground_unit_has_a_blast_value():
    for name in combat.GROUND:
        cmd = combat.range_command("u", name, 4)
        assert cmd and len(cmd.split()) >= 6, (name, cmd)


def test_a_packed_trebuchet_gets_the_hint_and_no_order(monkeypatch):
    server, g = setup(monkeypatch, {"t-1": trebuchet.NAME})
    assert any("Unpack the Trebuchet first" in c for c in server.log)
    assert not vars(g).get("ordering")


def test_a_packed_trebuchet_in_a_mixed_selection_stays_and_the_mangonel_shoots(monkeypatch):
    server, g = setup(monkeypatch, {"t-1": trebuchet.NAME, "o-1": "MANGONEL"})
    server.log.clear()
    g.click("Steve")
    assert any("aoe attackground o-1" in c for c in server.log)
    assert not any("aoe attackground t-1" in c for c in server.log)
    assert any("Unpack the Trebuchet first" in c for c in server.log)


def test_an_unpacked_trebuchet_shoots_at_the_point(monkeypatch):
    server, g = setup(monkeypatch, {"t-1": trebuchet.NAME})
    g.trebs = {"t-1": ["unpacked"]}
    stance.open_menu(g, "Steve", "t-1")
    g.menus["Steve"]("Steve", stance.ATTACK_GROUND, False)
    server.log.clear()
    g.click("Steve")
    assert f"aoe attackground t-1 20 {g.map.y(20, 10)} 10" in server.log
