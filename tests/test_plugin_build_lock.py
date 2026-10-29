"""Parallel test workers build the Paper plugin once, not once per process (#3570)."""
import threading
import time

from game import run


def test_two_callers_build_the_plugin_once(tmp_path, monkeypatch):
    """Two threads ask for the jar of a changed source at the same time: one build, both get the same jar."""
    monkeypatch.setattr(run.mc_check, "CACHE", str(tmp_path / "mc"))
    built = []

    def build(version, path):
        built.append(path)
        time.sleep(0.3)                       # the second caller waits here, on the lock
        open(path, "w").close()
    monkeypatch.setattr(run, "build_plugin", build)
    paths = []
    threads = [threading.Thread(target=lambda: paths.append(run.plugin_jar("26.3"))) for _ in range(2)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert len(built) == 1
    assert paths[0] == paths[1]
