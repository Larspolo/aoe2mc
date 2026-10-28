"""game/map_table.py: the summon command of the framed map has the block_pos of the frame. Minecraft logs
"Block-attached entity at invalid position: null" when a block-attached entity has no block_pos (#2931)."""
import re

from test_minimap_click import setup as table_setup


def test_the_frame_is_summoned_with_the_block_pos_of_its_own_block():
    server, g = table_setup()
    summon = next(c for c in server.log if "summon minecraft:glow_item_frame" in c)
    assert "summon minecraft:glow_item_frame 12 65 12 " in summon
    assert re.search(r"block_pos:\[I;12,65,12\]", summon)
