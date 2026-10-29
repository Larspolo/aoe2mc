"""#3777 (epic #3774): the trigger effects "Disable Object Deletion" and "Enable Object Deletion". The units of the
effect get or lose the tag aoe2mc.keep, which the Delete key of the game program skips (stance.delete); a selected
building gets the order "keep <ref> 1|0", and demolish.delete does nothing for a kept building (g.kept)."""
import numpy as np
from test_delete_loss import town
from test_delete_units import setup
from test_own_building_fall import HOUSE

import aoe2mc
from game import demolish, scenario, stance


def lines(on=True, area=(2, 3, 4, 5), selected=()):
    e = dict(type=aoe2mc.DISABLE_OBJECT_DELETION if on else aoe2mc.ENABLE_OBJECT_DELETION, message="", player=1,
             time=0, object=None, tile=[-1, -1], area=list(area), selected=list(selected))
    trig = dict(id=8, name="t", enabled=True, looping=False, effects=[e],
                conditions=[dict(type=aoe2mc.TIMER, timer=30, inverted=False)])
    files = aoe2mc.trigger_files([trig], 4, np.full((64, 64), 70, np.int16))[1]
    return files.get("data/aoe2mc/function/trigger/8.mcfunction", "").splitlines()


def test_disable_tags_the_units_in_the_area_and_enable_removes_the_tag():
    add, = lines()
    assert add.startswith("tag @e[tag=aoe2mc.p1,") and "x=8," in add and add.endswith(" add aoe2mc.keep")
    assert lines(on=False)[0].endswith(" remove aoe2mc.keep")


def test_a_selected_building_gives_the_keep_order():
    assert lines(area=(-1,) * 4, selected=[42])[-1] == 'data modify storage aoe2mc:orders list append value "keep 42 1"'
    assert lines(on=False, area=(-1,) * 4, selected=[42])[-1].endswith('"keep 42 0"')


def test_delete_does_not_kill_a_kept_unit():
    server, g = setup()
    server.keep = {"m-1"}
    stance.delete(g)
    assert "m-1" in server.entities and "v-1" not in server.entities


def test_a_kept_building_stays_after_delete_and_falls_after_enable():
    server, g = town()
    house = next(o for o in g.data["objects"] if o.get("footprint") == [HOUSE[0], HOUSE[2], HOUSE[1], HOUSE[3]])
    house["ref"] = 42
    command = server.command
    order = []
    server.command = lambda cmd: f'Storage {scenario.ORDERS} has the following contents: {{list: ["{order[0]}"]}}' \
        if cmd == f"data get storage {scenario.ORDERS} list" and order else command(cmd)
    order[:] = ["keep 42 1"]
    scenario.orders(g)
    assert g.kept == {42}
    assert not demolish.delete(g, "Steve", HOUSE) and not any(c.startswith("aoe destroy") for c in server.log)
    order[:] = ["keep 42 0"]
    scenario.orders(g)
    assert demolish.delete(g, "Steve", HOUSE)
