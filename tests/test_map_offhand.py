"""Each player of a converted world gets the map of the world in the off-hand once (#966): a line of the datapack
pulse (docs/datapack.md). The item frame at the spawn (#839) keeps its map."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import aoe2mc  # noqa: E402


def pulse(world):
    with open(os.path.join(world, "datapacks", "aoe2mc", "data", "aoe2mc", "function", "pulse.mcfunction")) as f:
        return f.read().splitlines()


def test_the_pulse_puts_the_map_in_the_off_hand_once(tiny_world):
    lines = pulse(tiny_world[0])
    give = [ln for ln in lines if "weapon.offhand" in ln]
    assert give == ["execute as @a[tag=!aoe2mc_map] run item replace entity @s weapon.offhand with "
                    "minecraft:filled_map[minecraft:map_id=0]"]
    assert lines.index("tag @a[tag=!aoe2mc_map] add aoe2mc_map") == lines.index(give[0]) + 1


def test_the_map_lines_are_no_work_sound_and_no_ambience(tiny_world):
    assert all("aoe2mc_map" not in ln for ln in aoe2mc.ambience_lines(["minecraft:plains"]))
    assert len(aoe2mc.MAP_PULSE) == 2


def test_the_item_of_the_frame_is_the_same_map(tiny_world):
    item = aoe2mc.map_item()
    assert str(item["id"]) == "minecraft:filled_map" and int(item["components"]["minecraft:map_id"]) == 0
    assert "minecraft:filled_map[minecraft:map_id=0]" in aoe2mc.MAP_PULSE[0]
