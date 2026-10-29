"""#3532: the button "Tech tree" in slot 6 of the Game menu opens a page of the buildings of train.TRAINS; a click on a
building shows its units and technologies by age, and an item that the civilization does not have is a gray pane."""
from urllib.parse import unquote

from test_gather import FakeServer, grid

from game import build, civs, diplomacy, gather, menu, techtree, train


def setup(civ=None):
    server = FakeServer({})
    g = gather.Gather(server, grid([[64] * 8 for _ in range(8)], [])).setup()
    if civ:
        g.data.setdefault("players", {})[str(g.player)] = {"civ": civ}
    return server, g


def click(server, g, slot):
    server.scores[menu.OBJECTIVE] = slot + 1
    n = len(server.log)
    g.clicks()
    return unquote(" ".join(c for c in server.log[n:] if c.startswith("aoe menu")))


def barracks(civ=None, all_techs=False):
    server, g = setup(civ)
    g.data["all_techs"] = all_techs
    diplomacy.open_menu(g, "Steve")
    click(server, g, diplomacy.TECH_TREE_SLOT)
    text = click(server, g, techtree.BUILDINGS.index("BARRACKS"))
    return text + click(server, g, techtree.NEXT) * (f"{techtree.NEXT}:paper" in text)   # the technologies (#3533)


def test_the_game_menu_button_shows_each_building():
    server, g = setup()
    diplomacy.open_menu(g, "Steve")
    assert "6:oak_sapling:Tech%20tree:" in server.log[-1]
    text = click(server, g, diplomacy.TECH_TREE_SLOT)
    for i, b in enumerate(train.TRAINS):
        assert f" {i}:" in text and b.replace("_", " ").title() in text


def test_the_barracks_shows_each_item_in_the_row_of_its_age():
    slots = techtree.pages(train.TRAINS["BARRACKS"])[0]
    assert all(s // techtree.WIDTH in (techtree.age(n), techtree.MORE) for s, n in slots.items())
    text = barracks()
    assert train.ITEMS[slots[min(slots)]][2] in text and "45:arrow:Back" in text


def missing():
    """A civilization and a barracks item that it does not have."""
    return next((c, n) for n in train.TRAINS["BARRACKS"] for c in sorted(civs.MISSING.get(n, ())) if c in techtree.CIVS)


def test_an_item_that_the_civilization_does_not_have_is_gray():
    civ, name = missing()
    text = f"gray_stained_glass_pane:{train.ITEMS[name][2]}:Not in the tech tree of {build.pretty(civ)}"
    assert text in barracks(civ)


def test_all_techs_gives_the_item():
    civ, name = missing()
    text = barracks(civ, all_techs=True)
    assert train.ITEMS[name][2] in text and f"gray_stained_glass_pane:{train.ITEMS[name][2]}" not in text


def test_no_item_is_left_out_and_a_full_page_goes_on():
    names = [f"X{i}" for i in range(30)]                             # no age: all in the Dark Age row
    ps = techtree.pages(names)
    assert sorted(n for p in ps for n in p.values()) == sorted(names) and len(ps) == 2
    assert set(ps[0]) == set(range(9)) | set(range(36, 45))
