"""The Missionary with a relic rides a horse as the Missionary does (#3061). The relic carriers of the monks and priests
stay evokers on foot."""
import units


def test_the_missionary_with_a_relic_is_a_mounted_monk():
    assert units.classify("MISSIONARY_WITH_RELIC") == units.classify("MISSIONARY")
    desc = units.classify("MISSIONARY_WITH_RELIC")
    assert str(desc["id"]) == "minecraft:horse"
    assert str(desc["Passengers"][0]["id"]) == "minecraft:evoker"


def test_the_monks_and_priests_with_a_relic_stay_on_foot():
    for name in ("MONK_WITH_RELIC", "PRIEST_WITH_RELIC"):
        assert str(units.classify(name)["id"]) == "minecraft:evoker", name
