"""#4073 (epic #3774): the trigger effect "Damage Object" on a selected building. The converter puts the order
"hurt <ref> <amount>" into the data storage aoe2mc:orders; the scenario mode of the game program changes the score
aoe_hp of the building with that reference (game/scenario.py hurt), as the order of a building type does (#3776)."""
import re
import types

from test_trigger_foundation import lines

import aoe2mc
from game import repair, scenario

ORDER = 'data modify storage aoe2mc:orders list append value "hurt {} {}"'
HOUSE = dict(kind="building", name="HOUSE", player=1, ref=7, footprint=[40, 48, 48, 56])
RECT = (40, 48, 48, 56)


def effect(q=50, selected=(7,)):
    return dict(type=aoe2mc.DAMAGE_OBJECT, message="", player=1, time=0, object=(None, None), tile=[-1, -1],
                area=[-1] * 4, quantity=q, selected=list(selected))


def test_the_trigger_function_stores_one_order_per_selected_building():
    assert ORDER.format(7, 50) in lines(effect())
    assert ORDER.format(7, -20) in lines(effect(-20))
    assert not any('"hurt' in line for line in lines(effect(0)))


def play(q, ref="7", hp=300, full=550, monkeypatch=None):
    log, score = [], {"hp": hp}
    uuid = repair.uuid(RECT)

    def command(cmd):
        log.append(cmd)
        if cmd == f"data get storage {scenario.ORDERS} list":
            return f'{{list: ["hurt {ref} {q}"]}}'
        if cmd == f"scoreboard players get {uuid} aoe_hp":
            return f"{uuid} has {score['hp']} [Hit points]"
        if m := re.fullmatch(rf"scoreboard players set {uuid} aoe_hp (-?\d+)", cmd):
            score["hp"] = int(m[1])
        return ""
    import repair as plain  # scenario imports repair by its plain name: a second module (#4447, #5398)
    for m in (repair, plain):
        monkeypatch.setattr(m, "full", lambda g, name, player, rect=None: full)
    g = types.SimpleNamespace(command=command, map=types.SimpleNamespace(T=4), data=dict(objects=[HOUSE]), sites=[],
                              peers=[], bots=(), player=1)
    for r, n in re.findall(scenario.ORDER_KINDS["hurts"], command(f"data get storage {scenario.ORDERS} list")):
        scenario.hurt(g, int(r), int(n))
    return g, score["hp"], log, uuid


def test_the_order_lowers_the_hit_points_of_the_selected_building(monkeypatch):
    _, hp, log, uuid = play(50, monkeypatch=monkeypatch)
    assert hp == 250 and f"aoe label {uuid}" in log


def test_a_negative_amount_heals_up_to_the_full_hit_points(monkeypatch):
    assert play(-100, monkeypatch=monkeypatch)[1] == 400
    assert play(-500, monkeypatch=monkeypatch)[1] == 550


def test_an_amount_above_the_hit_points_razes_the_building(monkeypatch):
    g, hp, log, uuid = play(400, monkeypatch=monkeypatch)
    assert hp == 300 and f"aoe destroy {uuid}" in log and uuid in g.sieged


def test_a_ref_that_is_no_building_gives_no_command(monkeypatch):
    _, hp, log, _ = play(50, ref="9", monkeypatch=monkeypatch)
    assert hp == 300 and not any(c.startswith("aoe ") or c.startswith("scoreboard") for c in log[1:])
