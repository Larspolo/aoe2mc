"""The target of a building is invisible to players (#636), and mc_shot can show the view of a player."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "game"))
import combat  # noqa: E402

from tools import mc_shot  # noqa: E402


def test_slime_of_a_building_has_the_invisibility_effect():
    summon = combat.building(combat.target_uuid([8, 8, 16, 16]), "HOUSE", 2, (8, 64, 8, 15, 104, 15))[0]
    assert "Invisible:1b" not in summon          # an armor stand tag: the server drops it on a slime
    assert 'active_effects:[{id:"minecraft:invisibility",duration:-1,show_particles:0b}]' in summon


def test_player_view_holds_the_player_in_each_view(tmp_path):
    views = [(1, 70, 2, 180, 20), (5, 80, 6, 90, 30)]
    mc_shot.add_data_pack(str(tmp_path), views, 101, 100, player=True)
    tick = (tmp_path / "datapacks/aoe2mc_shot/data/aoe2mc_shot/function/tick.mcfunction").read_text()
    assert "gamemode adventure @a[scores={aoe2mc_t=1}]" in tick
    assert "@a[scores={aoe2mc_t=40..139}] run tp @s 1 70 2 180 20" in tick
    assert "@a[scores={aoe2mc_t=140..}] run tp @s 5 80 6 90 30" in tick
    mc_shot.add_data_pack(str(tmp_path), views, 101, 100)
    tick = (tmp_path / "datapacks/aoe2mc_shot/data/aoe2mc_shot/function/tick.mcfunction").read_text()
    assert "gamemode spectator" in tick and "@a[scores={aoe2mc_t=40}] run tp" in tick
