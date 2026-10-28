"""The AoE2 lobby setting "Lock Teams" (#2934): with `game/run.py --unlock-teams` the Diplomacy page has a stance row,
a click goes Ally → Neutral → Enemy → Ally, gather.allied follows it and the chat tells the other player. Without
the option the page has no stance row."""
import os
import sys
import types

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "game"))
import diplomacy  # noqa: E402
import gather  # noqa: E402
import run  # noqa: E402
import savegame  # noqa: E402

ROW = 9 * (len(diplomacy.RESOURCES) + 1)                               # the slot of the stance of player 2


def side(unlock=True):
    g = types.SimpleNamespace(player=1, data={"unlock_teams": unlock}, menus={}, sent=[], bots=[],
                              players={"1": {"team": 1}, "2": {"team": 1}, "3": {}})
    g.command = lambda c: g.sent.append(c) or ""
    return g


def test_a_click_goes_ally_neutral_enemy_ally_and_allied_follows():
    g = side()
    assert gather.allied(g.players, 1, 2)
    for kind, ally in (("neutral", False), ("enemy", False), ("ally", True)):
        g.sent.clear()
        assert diplomacy.order(g, "aoe2mc", ROW) == 0
        assert diplomacy.stance(g, 2) == kind and gather.allied(g.players, 1, 2) is ally
        assert any(c.startswith("tellraw @a[team=p2] ") and kind.capitalize() in c for c in g.sent)
        assert any(c.startswith("aoe allies ") for c in g.sent) and any(c.startswith("aoe neutral ") for c in g.sent)


def test_the_page_has_a_stance_item_only_with_the_option():
    shown = {slot: n for slot, m, n, lore in diplomacy.items(side())}
    assert shown[ROW] == "Stance: Ally" and shown[ROW + 1] == "Stance: Enemy"
    g = side(unlock=False)
    assert all(slot < ROW for slot, *_ in diplomacy.items(g))
    assert diplomacy.order(g, "aoe2mc", ROW) == 0 and g.sent == [] and gather.allied(g.players, 1, 2)


def test_a_load_puts_the_saved_stances_back():
    g = side()
    diplomacy.order(g, "aoe2mc", ROW + 1)                              # player 3: enemy → ally
    new = side()
    savegame.load(new, {"players": {}, "stances": {n: dict(p) for n, p in g.players.items()}})
    assert gather.allied(new.players, 1, 3) and new.sent[-2].startswith("aoe allies ")


def test_the_option_sets_the_setting():
    assert run.SETTINGS["unlock_teams"] is False and "unlock_teams" in savegame.SETTINGS
