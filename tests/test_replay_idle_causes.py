"""Record IDs of trained villagers (#4063): in de-64.3 most idle villagers of the replay were trained units whose ID
had no name, so the replay never gave them the orders of the record."""
import aoe2mc


def obj(ref, name, player=1):
    return dict(kind="B" if name == "TOWN_CENTER" else "U", name=name, player=player, x=0, y=0, ref=ref)


def test_a_unit_takes_an_id_of_its_own_player():
    objects = [obj(5, "TOWN_CENTER"), obj(6, "TOWN_CENTER", 2)]
    timeline = [dict(time=0, player=1, kind="queue", objects=[5], name="VILLAGER_MALE", amount=1),
                dict(time=0, player=2, kind="queue", objects=[6], name="VILLAGER_MALE", amount=1),
                dict(time=40000, player=2, kind="order", objects=[11], target=6),      # the villager of player 2
                dict(time=40000, player=1, kind="move", objects=[12], tile=[1.0, 1.0])]
    names = aoe2mc.name_timeline(objects, timeline)
    assert names[11] == names[12] == "VILLAGER_MALE"


def test_a_wrong_match_does_not_skip_the_ids_of_the_other_player():
    objects = [obj(5, "TOWN_CENTER"), obj(6, "TOWN_CENTER", 2)]
    timeline = [dict(time=0, player=1, kind="queue", objects=[5], name="VILLAGER_MALE", amount=2),
                dict(time=0, player=2, kind="queue", objects=[6], name="VILLAGER_MALE", amount=1),
                dict(time=40000, player=2, kind="move", objects=[11], tile=[1.0, 1.0]),
                dict(time=90000, player=1, kind="move", objects=[40], tile=[1.0, 1.0]),   # far: projectiles took IDs
                dict(time=90000, player=1, kind="move", objects=[41], tile=[1.0, 1.0])]
    names = aoe2mc.name_timeline(objects, timeline)
    assert names[11] == names[40] == names[41] == "VILLAGER_MALE"


def test_an_unmatched_builder_is_a_villager_of_its_player():
    objects = [obj(5, "TOWN_CENTER")]
    timeline = [dict(time=0, player=1, kind="queue", objects=[5], name="VILLAGER_FEMALE", amount=1),
                dict(time=30000, player=1, kind="move", objects=[11], tile=[1.0, 1.0]),
                dict(time=60000, player=1, kind="build", objects=[11, 12], name="HOUSE", tile=[3.0, 4.0])]
    names = aoe2mc.name_timeline(objects, timeline)
    assert names[11] == names[12] == "VILLAGER_FEMALE"
