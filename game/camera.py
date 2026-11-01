"""
The camera mode of the game program (owner request 2026-11-01): fast moves over the map at one height, as the camera
of AoE2. A hotbar item (ITEM, in hotbar slot SLOT) switches the mode of its player. A right click puts the player onto
a floor UP blocks above the highest ground of the map; there it walks SPEEDS[n] times the vanilla walk speed (4.3
blocks per second). A second right click ends the mode: the player flies 12 blocks above the block under it, as after
a click of the "Go to" menu. A shift right click selects the next speed of SPEEDS, also in the mode.
Only on Paper: the plugin (Camera.java) sends the floor of barrier blocks to the client of this player only, so the
world, its rain and arrows, and the other players do not change. Above PLAIN the client widens its field of view: a
chat line asks the player once to set the client option "FOV Effects" to 0 % (a server cannot change it).
Minecraft features: barrier blocks (an invisible floor), the attributes movement_speed and block_interaction_range
(reach 0: no outline on the floor, and a click does not take a floor block away). Own logic: the floor of one player
(vanilla has no block for one player) and the walk speed (vanilla has no command for it), both in the plugin.
gather.Gather.clicks gives the item and calls click().
"""
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import amounts  # noqa: E402
import lang  # noqa: E402

SLOT = 1                                                           # hotbar slot of the item (key 2): free
ITEM = ('minecraft:carrot_on_a_stick[item_model="minecraft:spyglass",item_name="Camera",'
        "custom_data={aoe_camera:1b}]")
UP = 24                                                            # blocks: the floor above the highest ground
SPEEDS = (5, 10, 20)                                               # times the vanilla walk speed
START = 1                                                          # the index of the first speed
PLAIN = 5                                                          # the fastest speed with no wider view (Camera.MAX_WALK)


def give(g):
    """Put the item into hotbar slot SLOT of each player that has no camera item there (only Paper)."""
    if getattr(g, "paper", False):
        g.command(f"execute as {g.who} unless items entity @s hotbar.{SLOT} *[custom_data={{aoe_camera:1b}}] "
                  f"run item replace entity @s hotbar.{SLOT} with {ITEM}")


def in_hand(g, player):
    """True when player holds the camera item in the main hand."""
    return "passed" in g.command(f"execute if items entity {player} weapon.mainhand *[custom_data={{aoe_camera:1b}}]")


def floor(g):
    """(y, x0, z0, x1, z1): the floor UP blocks above the highest ground of g.map, over the whole map."""
    top = max((y for row in g.map.ground for y in row if y is not None), default=64)
    return top + UP, 0, 0, g.map.n - 1, g.map.n - 1


def speed(g, player):
    """The speed of player: an item of SPEEDS."""
    return SPEEDS[vars(g).setdefault("camera_speeds", {}).get(player, START)]


def on(g, player):
    """The plugin command of the mode of player with its floor and speed."""
    return f"aoe camera {player} on {' '.join(map(str, floor(g)))} {speed(g, player)}"


def click(g, player, shift=False):
    """A right click with the item: the mode on or off; a shift right click: the next speed. Returns the mode now."""
    active = "Camera: on" in g.command(f"aoe camera {player}")
    if shift:
        speeds = vars(g).setdefault("camera_speeds", {})
        speeds[player] = (speeds.get(player, START) + 1) % len(SPEEDS)
        if active:
            g.command(on(g, player))
        bar(g, player, lang.text("aoe2mc.camera.speed", speed(g, player)))
    elif active:
        g.command(f"aoe camera {player} off")
        active = False
        vars(g).setdefault("camera_off", set()).add(player)            # on, then off: the tutorial step (#5503)
        bar(g, player, lang.text("aoe2mc.camera.off"))
        vars(g).setdefault("camera_on", set()).discard(player)
        amounts.swap(g, player, False)                                 # the normal amounts again (#5537)
    else:
        g.command(on(g, player))
        active = True
        bar(g, player, lang.text("aoe2mc.camera.on", speed(g, player)))
        vars(g).setdefault("camera_on", set()).add(player)
        amounts.swap(g, player, True)                                  # the large amounts (#5537)
    hinted = vars(g).setdefault("camera_hinted", set())
    if speed(g, player) > PLAIN and player not in hinted:          # once per player
        hinted.add(player)
        g.command(f"tellraw {player} " + json.dumps(lang.text("aoe2mc.camera.fov", color="gray")))
    return active


def bar(g, player, text):
    g.command(f"title {player} actionbar " + json.dumps(text))


def after_end(g):
    """After the end of a game (#5538): the game loop stops, but the camera item still works, so the player can look
    around the map, as in AoE2. Read the use statistic of each person (as gather.Gather.clicks); only the camera item
    acts, other items do nothing. Returns the players that switched the mode or the speed."""
    import gather  # gather imports this module
    out = []
    for name in filter(None, g.people()):
        if not re.search(r"has [1-9]", g.command(f"scoreboard players get {name} aoe_use")):
            continue
        g.command(f"scoreboard players reset {name} aoe_use")
        if in_hand(g, name):
            click(g, name, "passed" in g.command(f"execute as {name} if predicate {gather.SNEAK}"))
            out.append(name)
    return out
