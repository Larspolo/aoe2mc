"""The sneak predicate of the control groups (#1633): an inline predicate in Minecraft 26.3 takes `type:`, not
`condition:` ("Failed to parse structure: No key type"), else a sneak click with a group item never saves the group."""
import shutil

import pytest

from game import gather


def test_the_sneak_predicate_has_the_26_3_key():
    assert gather.SNEAK.startswith('{type:"minecraft:entity_properties"') and "condition:" not in gather.SNEAK


@pytest.mark.mc
def test_a_server_parses_the_sneak_predicate(tiny_world, tmp_path):
    from test_mc_check import mojang_reachable
    if not mojang_reachable():
        pytest.skip("Mojang is not reachable")
    from game import run
    world = shutil.copytree(tiny_world[0], tmp_path / "W")
    with run.Game(world, server="vanilla") as game:
        out = game.command(f"execute if predicate {gather.SNEAK}")                   # the server: no entity
    assert "Test failed" in out and "Failed to parse" not in out                  # parsed; it does not sneak
