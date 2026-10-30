"""#4413: a recorded unit with an ORDER on a relic is a monk (aoe2mc.name_timeline): only a monk picks a relic up."""
import aoe2mc


def obj(ref, name, player=1):
    return dict(kind="B", name=name, player=player, x=0, y=0, ref=ref)


def test_a_unit_that_orders_on_a_relic_is_a_monk():
    objects = [obj(5, "MONASTERY"), obj(6, "TOWN_CENTER"), obj(7, "RELIC", 0)]
    timeline = [dict(time=1000, player=1, kind="queue", objects=[5], name="MONK", amount=1),
                dict(time=2000, player=1, kind="queue", objects=[6], name="VILLAGER", amount=1),   # after the monk
                dict(time=200000, player=1, kind="order", objects=[11], target=7)]
    assert aoe2mc.name_timeline(objects, timeline)[11] == "MONK"
