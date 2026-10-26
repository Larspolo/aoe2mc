"""
The hints of the available actions (#798, owner decision #797: the action bar). While units are selected, a
building is chosen or the first corner of the selection box is set, the line above the hotbar shows what the player
can do now: how to go on, how to cancel and how to deselect. The action bar fades after about 2 s, so tick() sends
the hint again while the state lasts, and at once when the state changes. With no selection the hint shows once,
after the change: a player who only walks around gets no line. gather.Gather.clicks calls tick().
"""
import json

REPEAT = 1.5                                                       # seconds: before the action bar fades
TEXTS = {                                                          # short: the action bar is one line
    "building": "Place the {building}: right click the ground · Cancel: /trigger aoe_build set 0",
    "corner": "Selection box: right click the other corner",
    "military": "{n} military unit{s} · Right click: attack an enemy, select all of a type · Empty box: deselect",
    "none": "Right click: select a unit · Wand: selection box",
    "villagers": "{n} villager{s} · Right click: gather, build, build menu · Empty box: deselect",
}


def state(g, player=None):
    """The hint state of player (None: a player with no own state) and its text."""
    from build import pretty
    if player in g.corners:
        return "corner", TEXTS["corner"]
    if building := getattr(g, "ghosts", {}).get(player, [None])[0]:
        return "building", TEXTS["building"].format(building=pretty(building))
    if army := g.selected & g.soldiers.keys():
        return "military", TEXTS["military"].format(n=len(army), s="s" * (len(army) != 1))
    if g.selected:
        return "villagers", TEXTS["villagers"].format(n=len(g.selected), s="s" * (len(g.selected) != 1))
    return "none", TEXTS["none"]


def tick(g):
    """Send the hint of each state: one command for the players with an own state (a corner, a chosen building), one
    for all others. Again after REPEAT seconds, at once after a change."""
    own = sorted(set(g.corners) | set(getattr(g, "ghosts", {})))
    targets = {p: state(g, p)[1] for p in own}
    targets["@a" + ("[" + ",".join(f"name=!{p}" for p in own) + "]") * bool(own)] = state(g)[1]
    now, shown = g.clock(), g.hints
    for p in [p for p in shown if p not in targets]:
        del shown[p]
    for target, text in targets.items():
        last = shown.get(target, (None, 0))
        if last[0] != text or now - last[1] >= REPEAT and text != TEXTS["none"]:   # the idle hint shows once
            g.command(f"title {target} actionbar " + json.dumps({"text": text, "color": "gray"}))
            shown[target] = (text, now)
