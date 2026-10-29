"""
The tech tree of the own civilization (#3532, part of #3531), as the AoE2 DE tech tree: the button "Tech tree" of the
Game menu (diplomacy.py) opens a page with one item for each building that trains or researches. A click on a
building shows its units and technologies by age, one column for each unit line (#3533): row 0 the Dark Age, row 1 the Feudal Age, row 2 the Castle Age,
row 3 the Imperial Age (the key "age" of data/train.jsonl). An item that the civilization does not have is a gray pane.
The tree only shows: a click on an item of a building page trains nothing. Slots 48-50 of each page show the tree of
the previous or next civilization of data/civs.jsonl (#3535); the tree opens with the own civilization.
"""
import copy
import os
import re
import sys
import textwrap

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
CIVS = [r["name"] for r in civs.ROWS]                              # the order of data/civs.jsonl
PREVIOUS, NAME, FOLLOWING = 48, 49, 50
OBJECTIVE = "aoe_techtree"                                          # the chat command /trigger aoe_techtree (#3670)
BONUSES = 46                                                       # the civilization bonuses and the team bonus (#3536)


def view(g, civ):
    """A copy of g in which the player has civilization civ: train.trains and civs.missing read it, and the game state
    of g does not change. A copy of g, not a civ argument: both functions and their helpers read civs.real(g)."""
    v = copy.copy(g)
    players = dict(g.data.get("players", {}))
    players[str(g.player)] = {**players.get(str(g.player), {}), "civ": civ}
    v.data = {**g.data, "players": players}
    return v


def civ_items(civ):
    """The items of slots 48-50: previous civilization, the name of the shown civilization, next civilization."""
    return [(PREVIOUS, "arrow", "Previous civilization", ""),
            (NAME, "paper", build.pretty(civ) if civ else "Your civilization", "The tech tree of this civilization"),
            (FOLLOWING, "spectral_arrow", "Next civilization", "")]


def bonus_items(civ):
    """The item of slot 46: the bonus lines of civ and its team bonus (the key "texts" of data/civs.jsonl, the text at
    the left of the AoE2 DE tech tree), lines of 50 characters at most. None for a civilization with no texts."""
    texts = civs.value("texts", civ, None)
    if not texts:
        return []
    lines = [w for b in texts["bonuses"] for w in textwrap.wrap("• " + b, 50, subsequent_indent="  ")]
    lines += [""] + textwrap.wrap(f"Team bonus: {texts['team']}", 50, subsequent_indent="  ")
    return [(BONUSES, "book", "Civilization bonuses", "\n".join(lines))]


def other(civ, slot):
    """The civilization before (slot 48) or after (slot 50) civ in CIVS, else None (no civilization slot)."""
    step = {PREVIOUS: -1, FOLLOWING: 1}.get(slot)
    return step and CIVS[((CIVS.index(civ) if civ in CIVS else -1 if step > 0 else 0) + step) % len(CIVS)]


def open_menu(g, player, civ=None):
    """The page of buildings: one item for each building of train.TRAINS (its build menu icon), of civilization civ
    (else the own one)."""
    civ = civ or civs.real(g)
    items = [(i, build.ICONS.get(b, "chest"), build.pretty(b), "Click: its units and technologies")
             for i, b in enumerate(BUILDINGS)] + bonus_items(civ) + civ_items(civ)
    items.append((ALL, "bricks", "Buildings", "All buildings of your civilization by age"))

    def click(p, slot, shift):
        if slot == ALL:
            return buildings(g, p)
        if (c := other(civ, slot)):
            return open_menu(g, p, c)
        return slot < len(BUILDINGS) and page(g, p, BUILDINGS[slot], civ=civ)
    menu.show(g, player, "Tech tree", items, click)


def age(name):
    return train.value("age", name) or build.AGE.get(name, 0)


def root(name, names):
    """The first item of the unit line of name (#3533): an upgrade follows "after", else the upgrade or the unit that
    gives its old unit (the key "upgrade": [old unit, new unit])."""
    if train.value("after", name) in names:
        return root(train.value("after", name), names)
    for old, _ in train.lines(name) if name in train.UPGRADES else ():
        if old in names:
            return root(old, names)
        before = next((n for n in names if n in train.UPGRADES and old in (new for _, new in train.lines(n))), None)
        if before:
            return root(before, names)
    return name


def columns(names):
    """The columns of names: one for each unit line (a unit and its upgrades, as the AoE2 DE tree), then one for each
    technology. Two items of one line in one age (Two-Handed Swordsman, Legionary) take two columns."""
    cols = {}
    for n in names:
        cols.setdefault(root(n, names), []).append(n)
    out = []
    for col in cols.values():
        while col:
            first = {age(n): n for n in reversed(col)}
            out.append(sorted(first.values(), key=col.index))
            col = [n for n in col if n not in first.values()]
    return sorted(out, key=lambda c: len(c) == 1 and c[0] not in train.UPGRADES
                  and train.ITEMS.get(c[0], (0, "book"))[1] == "book")


def pages(names):
    """The slots of names by page: [{slot: name}]. Each unit line has its column, each age its row; the items of the
    columns that do not fit go into row MORE, then onto the next page in the same layout, so that no item is left out."""
    cols = columns(names)
    out = []
    while cols:
        slots = {age(n) * WIDTH + i: n for i, col in enumerate(cols[:WIDTH]) for n in col}
        rest = [n for col in cols[WIDTH:] for n in col]
        slots |= {MORE * WIDTH + i: n for i, n in enumerate(rest[:WIDTH])}
        out.append(slots)
        rest = rest[WIDTH:]
        cols = [c for c in ([n for n in col if n in rest] for col in cols[WIDTH:]) if c]
    return out or [{}]


def item(g, building, name):
    """The menu item of one unit or technology: gray when the civilization does not have it (civs.missing)."""
    cost = " · ".join(f"{v} {r}" for r, v in train.price(g, name, building).items()) or "free"
    _, material, label = train.ITEMS.get(name, (0, "barrier", build.pretty(name)))
    if civs.missing(g, name):
        return GRAY, label, f"Not in the tech tree of {build.pretty(civs.real(g) or 'your civilization')}"
    return material, label, "\n".join([cost] + [train.HELP[name]] * bool(train.HELP.get(name)))


def page(g, player, building, number=0, civ=None):
    """The units and technologies of building (train.trains) by age of civilization civ (else the own one); slot 45 goes
    back, slot 53 to the next page."""
    civ = civ or civs.real(g)
    shown = view(g, civ)
    all_pages = pages(train.trains(shown, building))
    number = min(number, len(all_pages) - 1)
    items = [(s, *item(shown, building, n)) for s, n in all_pages[number].items()] + [BACK] + civ_items(civ)
    items += [(NEXT, "paper", "Next page", f"Page {number + 2} of {len(all_pages)}")] * (number + 1 < len(all_pages))

    def click(p, slot, shift):
        if slot == BACK[0]:
            return open_menu(g, p, civ)
        if (c := other(civ, slot)):
            return page(g, p, building, civ=c)
        if slot == NEXT and number + 1 < len(all_pages):
            return page(g, p, building, number + 1, civ)
    menu.show(g, player, f"Tech tree: {build.pretty(building)}", items, click)


def building_item(g, name):
    """The menu item of one building: gray when the civilization does not have it (civs.missing), else its cost and time."""
    if civs.missing(g, name):
        return GRAY, build.pretty(name), f"Not in the tech tree of {build.pretty(civs.real(g) or 'your civilization')}"
    cost = " · ".join(f"{v} {r}" for r, v in build.COSTS.get(name, {}).items()) or "free"
    return build.ICONS[name], build.pretty(name), f"{cost}\n{build.BUILD_TIMES.get(name, 0)} s"


def rows(names):
    """The slots of names by page: [{slot: name}], one row per age; the items after WIDTH in a row go onto the next
    page (pages() makes a column per unit line, but buildings have no lines)."""
    by_age = [[n for n in names if age(n) == a] for a in range(AGES)]
    count = max(1, *(-(-len(r) // WIDTH) for r in by_age))
    return [{a * WIDTH + i: n for a, r in enumerate(by_age) for i, n in enumerate(r[k * WIDTH:(k + 1) * WIDTH])}
            for k in range(count)]


def buildings(g, player, number=0):
    """The buildings with an icon in build.jsonl by age. A building of other civilizations only (civs.ONLY) is left
    out; slot 45 goes back to the page of buildings, slot 53 to the next page (as page())."""
    names = [n for n in build.ICONS if n not in civs.ONLY or civs.real(g) in civs.ONLY[n]]
    all_pages = rows(names)
    number = min(number, len(all_pages) - 1)
    items = [(s, *building_item(g, n)) for s, n in all_pages[number].items()] + [BACK]
    items += [(NEXT, "paper", "Next page", f"Page {number + 2} of {len(all_pages)}")] * (number + 1 < len(all_pages))

    def click(p, slot, shift):
        if slot == BACK[0]:
            return open_menu(g, p)
        if slot == NEXT and number + 1 < len(all_pages):
            return buildings(g, p, number + 1)
    menu.show(g, player, "Tech tree: Buildings", items, click)


def setup(g):
    g.command(f"scoreboard objectives add {OBJECTIVE} trigger")


def tick(g):
    """Enable the trigger, and open the tech tree for each person that used it (its score goes back to 0). Like
    flare.tick: the score selector first, so that a tick without a user costs one command."""
    who = getattr(g, "who", "@a")
    g.command(f"scoreboard players enable {who} {OBJECTIVE}")
    sel = who[:-1] + f",scores={{{OBJECTIVE}=1..}}]" if who.endswith("]") else who + f"[scores={{{OBJECTIVE}=1..}}]"
    if "passed" in g.command(f"execute if entity {sel}"):
        for name in g.people():
            if name and re.search(r" has [1-9]", g.command(f"scoreboard players get {name} {OBJECTIVE}")):
                g.command(f"scoreboard players set {name} {OBJECTIVE} 0")
                open_menu(g, name)
