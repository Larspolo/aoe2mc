"""The other airef DUC actions and the formations of up-target-objects and up-target-point (#5132): pack, unpack
and drop-relic reach the paths of the trebuchet and the monk, action-none does nothing, a formation is read with no
warning. The map of test_bot_gather (tile size 1), the soldiers of test_per_up_search.script()."""
import monk
import trebuchet
from test_per_up_search import run, script
from test_per_up_target import commands


def setup(name, key, unit):
    s, b, me = script()
    b.g.soldiers[key] = name
    b.g.game.entities[key] = {"Pos": (24.5, 64.0, 18.5), "Rotation": (0.0, 0.0)}
    run(s, f"(up-find-local c: {unit} c: 40) (set-goal 100 10) (set-goal 101 12)")
    assert s.ids[key] in s.search[1]["found"]
    return s, b


def test_unpack_and_pack_a_trebuchet():
    s, b = setup(trebuchet.NAME, "t1", "trebuchet")
    out = commands(b, lambda: run(s, "(up-target-point 100 action-unpack formation-line -1)"))
    assert "aoe speed t1 0" in out and trebuchet.state(b.g, "t1") == "unpacking"
    b.g.trebs["t1"] = ["unpacked", 0.0, []]
    run(s, "(up-target-point 100 action-pack formation-box -1)")
    assert trebuchet.state(b.g, "t1") == "packing" and not s.warned


def test_drop_relic_lays_the_relic_of_the_monk():
    s, b = setup("MONK", "mk", "monk")
    b.g.relics = [{"at": None, "monk": "mk", "home": None}]
    b.g.fetching, b.g.relic_time, b.g.relic_gold, b.g.carrier_at = {}, 0.0, 0.0, {}
    run(s, "(up-target-objects 0 action-drop-relic formation-flank -1)")
    assert monk.relics(b.g)[0]["monk"] is None and monk.relics(b.g)[0]["at"] is not None and not s.warned


def test_none_and_formations_give_no_warning():
    s, b = setup("MILITIA", "m3", "infantry-class")
    for f in ("formation-line", "formation-box", "formation-stagger", "formation-flank", "-1"):
        run(s, f"(up-target-point 100 action-move {f} -1)")
    run(s, "(up-target-point 100 action-none -1 -1)")
    assert not s.warned


def test_action_with_no_path_warns_once(capsys):
    s, b = setup("MILITIA", "m3", "infantry-class")
    for a in ("action-train", "action-research", "action-work", "action-transform"):
        run(s, f"(up-target-point 100 {a} -1 -1)")
        run(s, f"(up-target-point 100 {a} -1 -1)")
    err = capsys.readouterr().err
    assert all(err.count(a) == 1 for a in ("action-train", "action-research", "action-work", "action-transform"))
