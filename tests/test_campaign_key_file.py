"""#3771: Minecraft 26.3 writes the data storage aoe2mc:* to data/aoe2mc/command_storage.dat (seen in a world that a
Paper server saved). An old file name gave no keys, so the keys of scenario 1 did not go into scenario 2."""
import os

from game import run


def test_the_storage_file_is_the_one_of_minecraft_26_3():
    assert run.STORAGE == os.path.join("data", "aoe2mc", "command_storage.dat")


def test_keys_of_a_saved_world_are_read(tmp_path):
    run.put_keys(str(tmp_path), {"gold left": 7})
    assert (tmp_path / "data" / "aoe2mc" / "command_storage.dat").is_file()
    assert run.world_keys(str(tmp_path)) == {"gold left": 7}
