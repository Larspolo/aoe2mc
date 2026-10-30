"""#3776 (epic #3774): the trigger effect "Damage Object" on a building. The converter puts the order "damage <player>
<building> <x1> <y1> <x2> <y2> <amount>" into the data storage aoe2mc:orders; the scenario mode of the game program
changes the score aoe_hp of the target entity of each building of the player in the area (game/scenario.py damage)."""
import re
import types

from test_trigger_foundation import lines

import aoe2mc
from game import repair, scenario

ORDER = 'data modify storage aoe2mc:orders list append value "damage 1 HOUSE {} {} {} {} {}"'
HOUSE = dict(kind="building", name="HOUSE", player=1, footprint=[40, 48, 48, 56])   # middle tile (11, 13) at T = 4
RECT = (40, 48, 48, 56)


def effect(q=50, area=(12, 14, 8, 10), player=1):
    return dict(type=aoe2mc.DAMAGE_OBJECT, message="", player=player, time=0, object=("B", "HOUSE"), tile=[-1, -1],
                area=list(area), quantity=q, selected=[])


def test_the_trigger_function_stores_the_order_with_the_sorted_area():
    assert lines(effect()) == [ORDER.format(8, 10, 12, 14, 50)]
    assert lines(effect(-20, area=(-1,) * 4)) == [ORDER.format(-1, -1, -1, -1, -20)]
    assert lines(effect(0)) == []


def play(q, hp=300, area="8 10 12 14", full=550, monkeypatch=None):
    log, score = [], {"hp": hp}
    uuid = repair.uuid(RECT)

    def command(cmd):
        log.append(cmd)
        if cmd == f"data get storage {scenario.ORDERS} list":
            return f'{{list: ["damage 1 HOUSE {area} {q}"]}}'
        if cmd == f"scoreboard players get {uuid} aoe_hp":
            return f"{uuid} has {score['hp']} [Hit points]"
        if m := re.fullmatch(rf"scoreboard players set {uuid} aoe_hp (-?\d+)", cmd):
            score["hp"] = int(m[1])
        return ""
    monkeypatch.setattr(repair, "full", lambda g, name, player, rect=None: full)
    g = types.SimpleNamespace(command=command, map=types.SimpleNamespace(T=4), data=dict(objects=[HOUSE]), sites=[],
                              peers=[], bots=(), player=1)
    m = re.findall(scenario.ORDER_KINDS["damages"], command(f"data get storage {scenario.ORDERS} list"))
    for player, name, *a, n in m:
        scenario.damage(g, int(player), name, [int(v) for v in a], int(n))
    return g, score["hp"], log, uuid


def test_the_order_lowers_the_hit_points(monkeypatch):
    _, hp, log, uuid = play(50, monkeypatch=monkeypatch)
    assert hp == 250 and f"aoe label {uuid}" in log


def test_a_negative_amount_heals_up_to_the_full_hit_points(monkeypatch):
    assert play(-100, monkeypatch=monkeypatch)[1] == 400
    assert play(-500, monkeypatch=monkeypatch)[1] == 550


def test_an_amount_above_the_hit_points_razes_the_building(monkeypatch):
    g, hp, log, uuid = play(400, monkeypatch=monkeypatch)
    assert hp == 300 and f"aoe destroy {uuid}" in log and uuid in g.sieged


def test_a_building_outside_the_area_keeps_its_hit_points(monkeypatch):
    _, hp, log, _ = play(50, area="0 0 5 5", monkeypatch=monkeypatch)
    assert hp == 300 and not any(c.startswith("aoe ") for c in log)
