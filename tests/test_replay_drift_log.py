"""tools/replay_drift.py --server-log (#2464): keep the server log after the run, no server."""
import types

import replay_drift


def test_keep_log_copies_the_server_log(tmp_path):
    (tmp_path / "logs").mkdir()
    (tmp_path / "logs" / "latest.log").write_text("[aoe] no path for VILLAGER\n")
    out = tmp_path / "kept.log"
    replay_drift.keep_log(types.SimpleNamespace(folder=str(tmp_path)), str(out))
    assert out.read_text() == "[aoe] no path for VILLAGER\n"
    replay_drift.keep_log(types.SimpleNamespace(folder=str(tmp_path / "none")), str(tmp_path / "x.log"))
    assert not (tmp_path / "x.log").exists()                    # no server log: no file and no error


def test_the_option_goes_to_measure(monkeypatch, tmp_path):
    calls = []
    monkeypatch.setattr(replay_drift, "measure", lambda *a, **k: calls.append(a) or [])
    replay_drift.main(["REC", "--until", "00:30", "--server-log", str(tmp_path / "F.log")])
    replay_drift.main(["REC"])
    assert [c[-1] for c in calls] == [str(tmp_path / "F.log"), None]
