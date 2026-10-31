"""
The hints of the available actions (#798, owner decision #797: the action bar). While units are selected, a
building is chosen or the first corner of the selection box is set, the line above the hotbar shows what the player
can do now: how to go on, how to cancel and how to deselect. The action bar fades after about 2 s, so tick() sends
the hint again while the state lasts, and at once when the state changes. With no selection the hint shows once,
after the change: a player who only walks around gets no line. gather.Gather.clicks calls tick().
The pointed target (#989, gather.Gather.point) also goes into this line, after the count of the selection, so the
action bar keeps one writer.
"""
import json

import lang

ORDERS = ("attack_ground", "attack_move", "follow", "guard", "patrol")   # the menu items that wait for a click
REPEAT = 1.5                                                       # seconds: before the action bar fades
TEXTS = {                                                          # the keys of texts.jsonl; one line each
    "attack_ground": "aoe2mc.hints.attack_ground",
    "attack_move": "aoe2mc.hints.attack_move",
    "building": "aoe2mc.hints.building",
    "corner": "aoe2mc.hints.corner",
    "drag": "aoe2mc.hints.drag",
    "follow": "aoe2mc.hints.follow",
    "guard": "aoe2mc.hints.guard",
    "military": "aoe2mc.hints.military",
    "none": "aoe2mc.hints.none",
    "none-wand": "aoe2mc.hints.none_wand",
    "patrol": "aoe2mc.hints.patrol",
    "villagers": "aoe2mc.hints.villagers",
}


def hint(name, *args):
    """The text component of the hint name (TEXTS) with its arguments (lang.text)."""
    return lang.text(TEXTS[name], *args)


def count(kind, n):
    """The count of the selection in words: "1 villager", "3 villagers" (the plural is a key of its own)."""
    return lang.text(f"aoe2mc.hints.count_{kind}" + ("" if n == 1 else "_many"), n)


def state(g, player=None):
    """The hint state of player (None: a player with no own state) and its text (a text component)."""
    from build import pretty
    if player in getattr(g, "holds", {}):                          # Paper: a held right click (#992)
        return "drag", hint("drag")
    if player in g.corners:
        return "corner", hint("corner")
    if (order := getattr(g, "ordering", {}).get(player)) in ORDERS:   # the pending menu item (#3355, #3357, #3358)
        return order, hint(order)
    if building := getattr(g, "ghosts", {}).get(player, [None])[0]:
        return "building", hint("building", pretty(building))
    if player is not None:                                         # the own selection of player (#3486)
        g.person = player
    army, aim = g.selected & g.soldiers.keys(), getattr(g, "pointing", {}).get(player)
    box = lang.text("aoe2mc.hints.deselect_paper" if getattr(g, "paper", False) else "aoe2mc.hints.deselect")
    sel = None                                                     # the count of the selection, for a target
    if army:
        sel = count("military", len(army))
        kind, text = "military", hint("military", sel, box)
    elif g.selected:
        sel = count("villager", len(g.selected))
        kind, text = "villagers", hint("villagers", sel, box)
    else:
        kind, text = "none", hint("none" if getattr(g, "paper", False) else "none-wand")   # vanilla: the wand (#1786)
    if aim:                                                        # the count stays, the target replaces the help
        return "pointing", lang.text("aoe2mc.hints.pointing", sel, aim) if sel else aim
    return kind, text


def tick(g):
    """Send the hint of each state: one command for the players with an own state (a corner, a chosen building), one
    for all others. Again after REPEAT seconds, at once after a change."""
    if getattr(g, "noui", False):                                     # the cheat "noui" (#968)
        return
    own = sorted(set(g.corners) | set(getattr(g, "ghosts", {})) | set(getattr(g, "pointing", {})))
    targets = {p: state(g, p)[1] for p in own}
    import gather  # gather imports this module
    who = getattr(g, "who", "@a")                                      # two people: only the own team (#1310)
    targets[gather.only(who, *(f"name=!{p}" for p in own)) if own else who] = state(g)[1]
    now, shown = g.clock(), g.hints
    for p in [p for p in shown if p not in targets]:
        del shown[p]
    idle = (hint("none"), hint("none-wand"))
    for target, text in targets.items():
        last = shown.get(target, (None, 0))
        if last[0] != text or now - last[1] >= REPEAT and text not in idle:   # the idle hint shows once
            g.command(f"title {target} actionbar " + json.dumps(text | {"color": "gray"}))
            shown[target] = (text, now)
