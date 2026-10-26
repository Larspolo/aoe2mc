"""tools/replay_drift.py (#1139): the column "Still", the seconds that units stand still with a plugin order."""
import json

import replay_drift


def s(t, uuid, x, z, rx, rz, name="VILLAGER_MALE", order=True):
    return {"t": t * 1000, "uuid": uuid, "name": name, "x": x, "z": z, "rx": rx, "rz": rz, "order": order}


def test_a_unit_held_in_place_with_an_order_counts_and_a_walker_does_not():
    samples = [s(t, "held", 0, 0.1 * (t // 2), 10, 0) for t in range(0, 12, 2)]       # 10 blocks off, 0.1 per sample
    samples += [s(t, "walks", t, 0, 30, 0) for t in range(0, 12, 2)]                   # 2 blocks per sample
    samples += [s(t, "idle", 0, 0, 10, 0, "KNIGHT", order=False) for t in range(0, 12, 2)]   # no order: stuck only
    samples += [s(t, "near", 0, 0, 3, 0, "MILITIA") for t in range(0, 12, 2)]          # 3 blocks: on its way
    k = replay_drift.analyze(samples)
    assert k["VILLAGER"]["still"] == 10 and k["KNIGHT"]["still"] == 0 and k["MILITIA"]["still"] == 0
    lines = replay_drift.table(k).splitlines()
    assert lines[0].split()[-1] == "Still" and lines[1].split()[0] == "VILLAGER" and lines[1].split()[-1] == "10"


def test_the_slack_of_a_leg_and_a_sample_without_order_end_the_count():
    samples = [dict(s(0, "a", 0, 0, 10, 0), slack=8), dict(s(2, "a", 0, 0, 10, 0), slack=8)]   # 2 blocks less slack
    samples += [s(0, "b", 0, 0, 10, 0), s(2, "b", 0, 0, 10, 0, order=False), s(4, "b", 0, 0, 10, 0)]
    assert replay_drift.analyze(samples)["VILLAGER"]["still"] == 0


def test_read_prints_the_column(tmp_path, capsys):
    log = tmp_path / "drift.jsonl"
    log.write_text("".join(json.dumps(s(t, "a", 0, 0, 10, 0)) + "\n" for t in (0, 4)))
    replay_drift.main(["--read", str(log)])
    out = capsys.readouterr().out.splitlines()
    assert out[0].split()[-1] == "Still" and out[1].split()[-1] == "4"
