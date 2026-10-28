"""game/savegame.py: two saves in one second get two folders, so the second save does not stop the game (#3046)."""
import os

from game import savegame


def test_two_saves_in_one_second_get_two_folders(tmp_path, monkeypatch):
    world = tmp_path / "World"
    (world / "region").mkdir(parents=True)
    (world / "level.dat").write_text("one")
    monkeypatch.setattr(savegame.time, "strftime", lambda fmt: "20261028-110436")
    first = savegame.write(str(tmp_path / "saves"), str(world), {"n": 1})
    second = savegame.write(str(tmp_path / "saves"), str(world), {"n": 2})
    assert first != second
    assert os.path.basename(first) == "World-20261028-110436"
    assert os.path.basename(second) == "World-20261028-110436-2"
    assert savegame.read(first) == {"n": 1}
    assert savegame.read(second) == {"n": 2}
    assert os.path.isfile(os.path.join(second, "world", "level.dat"))
