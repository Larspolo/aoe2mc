"""
The tech tree of the own civilization (#3532, part of #3531), as the AoE2 DE tech tree: the button "Tech tree" of the
Game menu (diplomacy.py) opens a page with one item for each building that trains or researches. A click on a
building shows its units and technologies by age: row 0 the Dark Age, row 1 the Feudal Age, row 2 the Castle Age,
row 3 the Imperial Age (the key "age" of data/train.jsonl). An item that the civilization does not have is a gray pane.
The tree only shows: a click on an item of a building page trains nothing.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build  # noqa: E402
import civs  # noqa: E402
import menu  # noqa: E402
import train  # noqa: E402

BUILDINGS = list(train.TRAINS)                                     # the page of buildings, in the order of train.TRAINS
AGES = 4                                                           # rows 0-3: Dark, Feudal, Castle, Imperial Age
WIDTH = 9                                                          # items of one row
MORE = 4                                                           # the row of the items that do not fit in their age row
BACK = (45, "arrow", "Back", "The page of buildings")
ALL = 45                                                           # slot of the page of buildings: all buildings (#3534)
NEXT = 53
GRAY = "gray_stained_glass_pane"


def open_menu(g, player):
    """The page of buildings: one item for each building of train.TRAINS (its build menu icon), and slot 45 for all."""
    items = [(i, build.ICONS.get(b, "chest"), build.pretty(b), "Click: its units and technologies")
             for i, b in enumerate(BUILDINGS)]
    items.append((ALL, "bricks", "Buildings", "All buildings of your civilization by age"))

    def choose(p, slot, shift):
        if slot == ALL:
            return buildings(g, p)
        return slot < len(BUILDINGS) and page(g, p, BUILDINGS[slot])
    menu.show(g, player, "Tech tree", items, choose)


def pages(names):
    """The slots of names by page: [{slot: name}]. Each age has its row; the items that do not fit go into row MORE,
    then onto the next page in the same layout, so that no item is left out."""
    rows = [[n for n in names if (train.value("age", n) or build.AGE.get(n, 0)) == a] for a in range(AGES)]
    out = []
    while any(rows):
        slots = {a * WIDTH + i: n for a, row in enumerate(rows) for i, n in enumerate(row[:WIDTH])}
        rest = [n for row in rows for n in row[WIDTH:]]
        slots |= {MORE * WIDTH + i: n for i, n in enumerate(rest[:WIDTH])}
        out.append(slots)
        rest = rest[WIDTH:]
        rows = [[n for n in row[WIDTH:] if n in rest] for row in rows]
    return out or [{}]


def item(g, building, name):
    """The menu item of one unit or technology: gray when the civilization does not have it (civs.missing)."""
    cost = " · ".join(f"{v} {r}" for r, v in train.price(g, name, building).items()) or "free"
    _, material, label = train.ITEMS.get(name, (0, "barrier", build.pretty(name)))
    if civs.missing(g, name):
        return GRAY, label, f"Not in the tech tree of {build.pretty(civs.real(g) or 'your civilization')}"
    return material, label, "\n".join([cost] + [train.HELP[name]] * bool(train.HELP.get(name)))


def page(g, player, building, number=0):
    """The units and technologies of building (train.trains) by age; slot 45 goes back, slot 53 to the next page."""
    all_pages = pages(train.trains(g, building))
    number = min(number, len(all_pages) - 1)
    items = [(s, *item(g, building, n)) for s, n in all_pages[number].items()] + [BACK]
    items += [(NEXT, "paper", "Next page", f"Page {number + 2} of {len(all_pages)}")] * (number + 1 < len(all_pages))

    def click(p, slot, shift):
        if slot == BACK[0]:
            return open_menu(g, p)
        if slot == NEXT and number + 1 < len(all_pages):
            return page(g, p, building, number + 1)
    menu.show(g, player, f"Tech tree: {build.pretty(building)}", items, click)


def building_item(g, name):
    """The menu item of one building: gray when the civilization does not have it (civs.missing), else its cost and time."""
    if civs.missing(g, name):
        return GRAY, build.pretty(name), f"Not in the tech tree of {build.pretty(civs.real(g) or 'your civilization')}"
    cost = " · ".join(f"{v} {r}" for r, v in build.COSTS.get(name, {}).items()) or "free"
    return build.ICONS[name], build.pretty(name), f"{cost}\n{build.BUILD_TIMES.get(name, 0)} s"


def buildings(g, player, number=0):
    """The buildings with an icon in build.jsonl by age. A building of other civilizations only (civs.ONLY) is left
    out; slot 45 goes back to the page of buildings, slot 53 to the next page (as page())."""
    names = [n for n in build.ICONS if n not in civs.ONLY or civs.real(g) in civs.ONLY[n]]
    all_pages = pages(names)
    number = min(number, len(all_pages) - 1)
    items = [(s, *building_item(g, n)) for s, n in all_pages[number].items()] + [BACK]
    items += [(NEXT, "paper", "Next page", f"Page {number + 2} of {len(all_pages)}")] * (number + 1 < len(all_pages))

    def click(p, slot, shift):
        if slot == BACK[0]:
            return open_menu(g, p)
        if slot == NEXT and number + 1 < len(all_pages):
            return buildings(g, p, number + 1)
    menu.show(g, player, "Tech tree: Buildings", items, click)
