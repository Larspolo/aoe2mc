"""A broken ZR@ random map archive stops with an OptionError that names the file (#5405)."""
import zipfile

import pytest

import aoe2mc


def test_an_archive_without_a_script_names_the_file(tmp_path):
    archive = tmp_path / "ZR@empty.rms"
    with zipfile.ZipFile(archive, "w") as z:
        z.writestr("readme.txt", "no script here")
    with pytest.raises(aoe2mc.OptionError, match="ZR@empty.rms: no .rms script in the archive"):
        aoe2mc.read_rms(str(archive), 1)


def test_an_archive_with_scripts_none_named_like_the_file_lists_them(tmp_path):
    archive = tmp_path / "ZR@big.rms"
    with zipfile.ZipFile(archive, "w") as z:
        z.writestr("a.rms", "<LAND_GENERATION>\n")
        z.writestr("b.rms", "<LAND_GENERATION>\n")
    with pytest.raises(aoe2mc.OptionError, match="ZR@big.rms") as err:
        aoe2mc.read_rms(str(archive), 1)
    assert "a.rms" in str(err.value) and "b.rms" in str(err.value)


def test_a_damaged_zip_names_the_file(tmp_path):
    archive = tmp_path / "ZR@broken.rms"
    archive.write_bytes(b"PK\x03\x04" + b"not really a zip archive" * 4)
    with pytest.raises(aoe2mc.OptionError, match="ZR@broken.rms: not a valid zip archive"):
        aoe2mc.read_rms(str(archive), 1)
