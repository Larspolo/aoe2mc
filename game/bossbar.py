"""
The boss bar of the selected unit (#659, part of #657), as the unit panel of AoE2: the name of the unit that the
player clicked last, the number of selected units, and its hit points. Minecraft has the feature: one `bossbar` per
player, and `execute store result bossbar` copies the values of the entity (`max_health` attribute, `Health`) into
it. So the program keeps no hit points of its own. gather.Gather.select calls show(), Gather.step calls tick().
"""
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import lang  # noqa: E402

from units import pretty  # noqa: E402


def bar(g):
    return f"aoe2mc:sel_p{g.player}"


def setup(g):
    for c in (f'bossbar add {bar(g)} ""', f"bossbar set {bar(g)} color red", f"bossbar set {bar(g)} style notched_10",
              f"bossbar set {bar(g)} visible false"):
        g.command(c)


def name(g, uuid):
    return g.soldiers.get(uuid) or getattr(g, "prey", {}).get(uuid) or next((o["name"] for o in g.units if o["uuid"] == uuid), "")


def show(g, uuid):
    """Show unit uuid (the last click) on the bar, and the number of selected units when there are more than one."""
    if uuid is None:
        return hide(g)
    g.bar, n = uuid, len(g.selected)
    stance = getattr(g, "stances", {}).get(uuid)                       # not aggressive (#1107)
    rest = (f" ({n})" if n > 1 else "") + (f" · {pretty(stance)}" if stance else "")
    text = [lang.name(name(g, uuid))] + ([rest] if rest else [])      # a translate key (#5346)
    for c in (f"bossbar set {bar(g)} name {json.dumps(text)}", f"bossbar set {bar(g)} players" + f" {getattr(g, 'who', '@a')}" * (not g.noui),
              f"execute store result bossbar {bar(g)} max run attribute {uuid} minecraft:max_health get"):
        g.command(c)
    if tick(g):
        g.command(f"bossbar set {bar(g)} visible true")


def hide(g):
    g.bar = None
    g.command(f"bossbar set {bar(g)} visible false")


def tick(g):
    """Copy the health of the unit into the bar. A dead (0 health) or unloaded unit hides the bar. Returns True when it is shown."""
    if g.bar is None:
        return False
    out = g.command(f"execute store result bossbar {bar(g)} value run data get entity {g.bar} Health")
    if "No entity was found" in out or re.search(r": 0(\.0)?f", out):           # a dying mob stays for 20 ticks
        hide(g)
        return False
    return True
