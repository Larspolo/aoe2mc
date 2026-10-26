"""tools/replay_drift.py (#813): the table of the distances between the units and their replay positions."""
import types

import replay_drift


def s(t, uuid, x, z, rx, rz, name="VILLAGER_MALE"):
    return {"t": t * 1000, "uuid": uuid, "name": name, "x": x, "z": z, "rx": rx, "rz": rz}


def test_stuck_stray_and_died_units():
    samples = [s(t, "a", 0, 0, 0, 0) for t in range(0, 60, 10)]                      # on its position
    samples += [s(t, "b", 0, 0, 10, 0) for t in range(0, 60, 10)]                    # 10 blocks off for 50 s: stuck
    samples += [s(0, "c", 0, 0, 0, 0), s(10, "c", 5, 0, 0, 0)]                       # moved 5 blocks, no order: stray
    samples += [s(0, "d", 0, 0, 0, 0), s(10, "d", None, None, 0, 0)]                 # gone: died
    samples += [s(0, "e", 0, 0, 10, 0, "KNIGHT"), s(20, "e", 0, 0, 10, 0, "KNIGHT")]  # 20 s far: not stuck yet
    k = replay_drift.analyze(samples)
    assert k["VILLAGER"] == {"units": 4, "stuck": 1, "stray": 1, "died": 1, "median": 0.0, "max": 10.0,
                              "still": 0}
    assert k["KNIGHT"]["stuck"] == 0 and k["KNIGHT"]["median"] == 10.0
    lines = replay_drift.table(k).splitlines()
    assert lines[0].split() == ["Unit", "Units", "Median", "Max", "Stuck", "Stray", "Died", "Still"]
    assert lines[1].split() == ["VILLAGER", "4", "0.0", "10.0", "1", "1", "1", "0"]


def test_a_new_replay_target_an_order_or_a_fight_is_not_stray():
    k = replay_drift.analyze([s(0, "a", 0, 0, 0, 0), s(10, "a", 8, 0, 8, 0)])
    assert k["VILLAGER"]["stray"] == 0
    for flag in ("order", "target"):
        k = replay_drift.analyze([s(0, "a", 0, 0, 9, 0), dict(s(10, "a", 6, 0, 9, 0), **{flag: True})])
        assert k["VILLAGER"]["stray"] == 0


def test_where_reads_all_pages():
    units = [f"u{i:03d} {i}.00 64.00 1.50 {i % 2} 0" for i in range(45)]

    def command(c):
        start = int(c.split()[-1])
        return f"Where 45: {', '.join(units[start:start + 40])}"
    got = replay_drift.where(types.SimpleNamespace(command=command), "@e[tag=aoe2mc.pop]")
    assert len(got) == 45 and got["u044"] == (44.0, 64.0, 1.5, False, False) and got["u001"][3]


def test_where_of_no_unit():
    assert replay_drift.where(types.SimpleNamespace(command=lambda c: "Where 0: "), "@e") == {}


def test_the_rest_of_a_leg_is_no_distance():
    walk = [dict(s(t, "a", 3 * t, 0, 40, 0), slack=40 - 3 * t) for t in range(0, 14, 2)]   # 3 blocks/s to its leg end
    k = replay_drift.analyze(walk)
    assert k["VILLAGER"]["max"] == 0.0 and k["VILLAGER"]["median"] == 0.0
