"""The plugin keys the help lines by material:label (#1659): two items with the same key show one help line."""
from collections import defaultdict

from game import build, train


def test_only_a_unit_and_its_upgrade_share_a_lore_key_and_the_upgrade_comes_last():
    keys = defaultdict(list)
    for name in sorted(train.HELP):                                    # the order of train.lore()
        for material in (train.ITEMS[name][1], build.LOCKED):
            keys[material, train.ITEMS[name][2]].append(name)
    for (material, _), names in keys.items():
        if len({train.HELP[n] for n in names}) > 1:                    # the gray item shows the upgrade (#1160)
            assert material == build.LOCKED and names == [names[0], names[0] + "_UPGRADE"], names
