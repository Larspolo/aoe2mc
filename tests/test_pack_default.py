"""The launcher checks the resource pack box by default (#5898); the box stays."""
import gui


def test_the_pack_box_starts_checked_and_passes_the_option():
    assert "resource_pack" in gui.ON and "resource_pack" in dict(gui.FLAGS)
    assert "--resource-pack" in gui.argv({"input": "a.aoe2scenario", "output": "/s/a"} | dict.fromkeys(gui.ON, True))
