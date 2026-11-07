"""The icons of the editor palette (#6057): each object shows the item of its look, not the icon of its tab."""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "game"))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import editor  # noqa: E402
import mcvalid  # noqa: E402
import menu  # noqa: E402

SAMPLE = {"units": ("MILITIA", "KNIGHT", "GALLEY"), "heroes": None, "resources": ("FORAGE_BUSH",), "cliffs": None,
          "gaia": ("RELIC",)}                                         # None: the first name of the tab


def is_item(i):
    return i.endswith(("_spawn_egg",) + editor.VEHICLES) or i in editor.ITEM_OF.values() or mcvalid.block_error(i) is None


def test_a_sample_of_each_tab_has_its_own_icon():
    tabs = dict(editor.tabs())
    names = list(tabs)
    for t, sample in SAMPLE.items():
        for n in sample or tabs[t][:1]:
            i = editor.icons().get(n)
            assert n in tabs[t] and i and i != editor.TAB_ICONS[names.index(t)] and is_item(i), (t, n, i)


def test_a_mount_shows_its_rider_and_all_icons_are_items():
    assert editor.icon("KNIGHT").endswith("_spawn_egg") and editor.icon("KNIGHT") != "horse_spawn_egg"
    assert editor.icon("GALLEY").endswith("boat")
    assert all(is_item(i) for i in editor.icons().values())


def test_the_palette_shows_the_icons(monkeypatch):
    shown = []
    monkeypatch.setattr(menu, "show", lambda g, p, title, items, click: shown.extend(items))
    editor.open_menu(None, "p", tab=0)
    first = dict(editor.tabs())["units"][0]
    assert shown[0][1] == editor.icons()[first]
