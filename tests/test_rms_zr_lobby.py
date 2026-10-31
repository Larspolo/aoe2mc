"""A ZR@ random map archive takes the lobby options --players and --map-size like a plain .rms script (#5406)."""
import json
import zipfile

import aoe2mc

SCRIPT = "<LAND_GENERATION>\nbase_terrain GRASS\n"


def test_a_zr_archive_gives_the_lobby_players_and_map_size(tmp_path):
    archive = tmp_path / "ZR@lobby.rms"
    with zipfile.ZipFile(archive, "w") as z:
        z.writestr("lobby.rms", SCRIPT)
    out = tmp_path / "W"
    aoe2mc.main([str(archive), str(out), "--players", "3", "--map-size", "60", "--no-units"])
    assert json.loads((out / "aoe2mc.json").read_text())["lobby"]["map_size"] == "60"

    size, _, _, _, _, _, players = aoe2mc.read_rms(str(archive), 1, 3, size=aoe2mc.map_size("60"))
    assert size == 60
    assert len([p for p in players if p > 0]) == 3           # player 0 is GAIA
