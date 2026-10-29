"""The production panel names a trained villager "Villager", as AoE2 does (#3740). Fake RCON."""
from test_replay_production_panel import make


def test_the_panel_of_a_town_center_names_the_villager_villager():
    (summon,) = make().panel(500)
    assert '"text": "Villager [..........]"' in summon and "Male" not in summon
