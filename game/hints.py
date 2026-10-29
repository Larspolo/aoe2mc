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

REPEAT = 1.5                                                       # seconds: before the action bar fades
TEXTS = {                                                          # short: the action bar is one line
    "building": "Place the {building}: right click the ground · Shift + right click: place more · Cancel: /trigger aoe_build set 0",
    "corner": "Selection box: right click the other corner",
    "drag": "Selection box: hold right click, look at the other corner, release · Release here: cancel",
    "military": "{n} military unit{s} · Right click: attack an enemy, stance menu · Empty box: deselect",
    "patrol": "Patrol: right click the ground",
    "none": "Right click: select a unit · Hold right click: selection box",
    "none-wand": "Right click: select a unit · Wand: selection box",
    "villagers": "{n} villager{s} · Right click: gather, build, build menu · Empty box: deselect",
}


def state(g, player=None):
    """The hint state of player (None: a player with no own state) and its text."""
    from build import pretty
    if player in getattr(g, "holds", {}):                          # Paper: a held right click (#992)
        return "drag", TEXTS["drag"]
    if player in g.corners:
        return "corner", TEXTS["corner"]
    if getattr(g, "ordering", {}).get(player) == "patrol":         # the Patrol menu item (#3355)
        return "patrol", TEXTS["patrol"]
    if building := getattr(g, "ghosts", {}).get(player, [None])[0]:
        return "building", TEXTS["building"].format(building=pretty(building))
    if player is not None:                                         # the own selection of player (#3486)
        g.person = player
    army, aim = g.selected & g.soldiers.keys(), getattr(g, "pointing", {}).get(player)
    if army:
        kind, text = "military", TEXTS["military"].format(n=len(army), s="s" * (len(army) != 1))
    elif g.selected:
        kind, text = "villagers", TEXTS["villagers"].format(n=len(g.selected), s="s" * (len(g.selected) != 1))
    else:
        kind, text = "none", TEXTS["none" if getattr(g, "paper", False) else "none-wand"]   # vanilla: the wand (#1786)
    if getattr(g, "paper", False):                                 # Paper: a left click deselects (#1788)
        text = text.replace("Empty box: deselect", "Left click: deselect")
    if aim:                                                        # the count stays, the target replaces the help
        return "pointing", (text.split(" · ")[0] + " · " if g.selected else "") + aim
    return kind, text


def tick(g):
    """Send the hint of each state: one command for the players with an own state (a corner, a chosen building), one
    for all others. Again after REPEAT seconds, at once after a change."""
    if getattr(g, "noui", False):                                     # the cheat "noui" (#968)
        return
    own = sorted(set(g.corners) | set(getattr(g, "ghosts", {})) | set(getattr(g, "pointing", {})))
    targets = {p: state(g, p)[1] for p in own}
    import gather                                                      # gather imports this module
    who = getattr(g, "who", "@a")                                      # two people: only the own team (#1310)
    targets[gather.only(who, *(f"name=!{p}" for p in own)) if own else who] = state(g)[1]
    now, shown = g.clock(), g.hints
    for p in [p for p in shown if p not in targets]:
        del shown[p]
    for target, text in targets.items():
        last = shown.get(target, (None, 0))
        if last[0] != text or now - last[1] >= REPEAT and text not in (TEXTS["none"], TEXTS["none-wand"]):   # the idle hint shows once
            g.command(f"title {target} actionbar " + json.dumps({"text": text, "color": "gray"}))
            shown[target] = (text, now)
