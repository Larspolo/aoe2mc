"""The map editor mode of the game program (#5999, epic #5998).

    python3 game/run.py WORLD --editor OUT.aoe2scenario

The world starts with no game time: no play(), so no gather tick, no bot, no age, no victory and no fog. The units
and buildings stand still. The person paints the terrain with the creative inventory (run.py sets creative mode) and
places water. The chat word `save` and the stop of the server write a save folder (savegame.write, no game state)
and export it to OUT (export.export): export.ground() gives each painted tile the AoE2 terrain of its new top block.
Vanilla logs each chat line ("<name> text"), so the log of the server is enough: no plugin command.
The chat word `palette` opens the palette of objects (#6013): tabs Units, Buildings and Resources; a right click on an
object places it where the person looks (place), and the save keeps it.
The chat word `remove` removes the object that the person looks at (#6002): its entities, the blocks of a building
or resource down to the ground of its tiles, and its entry of the save (State.removed: start objects; State.placed).
The chat word `players` opens the players menu (#6003): the current player of the palette, and the civilization, the
start resources and the starting age of each player. They go into the players of aoe2mc.json (State.data), and save
writes that file into the save folder: export.export reads them there, with no new code path.
"""
import json
import os
import re
import time

import export
import gather
import lang
import menu
import numpy as np
import savegame

REMOVE = re.compile(r"INFO\]: (?:\[Not Secure\] )?<(\w{1,16})> remove\s*$")    # the chat word of remove (#6002)
PALETTE = re.compile(r"INFO\]: (?:\[Not Secure\] )?<(\w{1,16})> palette\s*$")   # the chat word of the palette (#6013)
PLAYERS = re.compile(r"INFO\]: (?:\[Not Secure\] )?<(\w{1,16})> players\s*$")   # the players menu (#6003)
CHAT = re.compile(r"INFO\]: (?:\[Not Secure\] )?<(\w{1,16})> save\s*$")   # the chat word, as the server logs it


class State:
    """The light state of the editor (#6012): no Gather, but what menu, build.free and build.found need: the map of
    aoe2mc.json, the open chest menus, command, and the list of placed objects (AoE2 unit ID, owner, tile)."""

    def __init__(self, game, data=None):
        if data is None:
            with open(os.path.join(game.world, "aoe2mc.json")) as f:
                data = json.load(f)
        self.game, self.data, self.map = game, data, gather.Map(data)
        self.menus, self.placed, self.person, self.picked = {}, [], None, {}   # picked: player -> object name
        self.removed = set()                                           # the indices of removed start objects (#6002)
        self.player = PLAYER                                          # the owner of the next object (#6003)

    def command(self, cmd):
        return self.game.command(cmd)

    pos, look = gather.Gather.pos, gather.Gather.look                  # the eye of the person (data get entity)

    def place(self, unit_id, player, tile):
        """Add an object to the save: tile (x, y) in the tiles of the world."""
        self.placed.append({"id": int(unit_id), "player": int(player), "tile": [float(v) for v in tile]})

    def dump(self):
        return {"placed": list(self.placed), "removed": sorted(self.removed)}


HIGH = 40                                                              # blocks over the ground that remove clears
PAGE = 45                                                              # items per page; the last row: the tabs
TAB_ICONS = ("armor_stand", "bricks", "gold_ore")                      # Units, Buildings, Resources (lang keys)
PLAYER = 1                                                             # the first current player


def tabs():
    """The palette tabs (#6013): [(tab, [object names])], from the data files: the units of train, the buildings of
    the build menu, the mines, fish and hunts of gather, the forest trees and the bushes of
    rmap (#6016). Only names with an AoE2 unit ID (export.unit_id)."""
    import build
    import train

    import rmap
    known = lambda names: [n for n in dict.fromkeys(names) if export.unit_id(n) is not None]   # noqa: E731
    return [("units", known(r["name"] for r in train.UNIT_ROWS)), ("buildings", known(build.MENU)),
            ("resources", known([t["name"] for t in gather.ROWS if {"mine", "fish", "hunt"} & set(t)] +
                                 sorted(set(rmap.FOREST_TREES.values())) +
                                 [n for n in sorted(rmap.OBJECTS) if "BUSH" in n]))]


def open_menu(g, player, tab=0, page=0):
    """Show tab of the palette at page. A click on a tab opens it; a click on an object picks it (the next right click
    places it), a right click on an object places it at once where the person looks."""
    import build
    all_tabs = tabs()
    names = all_tabs[tab][1]
    shown = names[page * PAGE:(page + 1) * PAGE]
    pages = max(1, -(-len(names) // PAGE))

    def click(p, slot, shift, right=False):
        if slot >= PAGE + len(all_tabs) and slot - PAGE - len(all_tabs) < 2:   # the page buttons
            open_menu(g, p, tab, (page + (1 if slot == PAGE + len(all_tabs) + 1 else -1)) % pages)
        elif slot >= PAGE:
            if slot - PAGE < len(all_tabs):
                open_menu(g, p, slot - PAGE)
        elif slot < len(shown):
            g.picked[p] = shown[slot]
            if right and (view := g.look(p)):
                place(g, p, shown[slot], *view)
    items = [(i, build.ICONS.get(n, TAB_ICONS[tab]), build.pretty(n), "") for i, n in enumerate(shown)]
    items += [(PAGE + k, TAB_ICONS[k], t.title(), "")
              for k, (t, _) in enumerate(all_tabs)]
    if pages > 1:
        items += [(PAGE + len(all_tabs), "arrow", "<", f"{page + 1}/{pages}"),
                  (PAGE + len(all_tabs) + 1, "spectral_arrow", ">", f"{page + 1}/{pages}")]
    return menu.show(g, player, "Palette", items, click)


def kind(name):
    """"B" (a building), "U" (a unit or an animal: an entity) or "O" (another object: its blocks), as the converter
    (aoe2mc.object_kinds)."""
    import aoe2mc
    return aoe2mc.object_kinds(old=False).get(export.unit_id(name), ("U",))[0][:1]


def place(g, player, name, eye, d):
    """Place object name of PLAYER (an animal: of Gaia) at the ground that the person looks at: a building finished, a
    unit as an entity (units.make_entity), a resource with its blocks. Not on the footprint of another object
    (build.free). Returns the placed object (dict of State.placed) or None."""
    import build
    import replay

    import units
    cell = g.map.pick_ground(eye, d)
    if cell is None:
        return None
    k, T = kind(name), g.map.T
    rect = build.area(g, name, cell) if k == "B" else (cell[0] // T * T, cell[0] // T * T + T, cell[1] // T * T,
                                                       cell[1] // T * T + T)
    if not build.free(g, rect):
        build.say(g, player, lang.text("aoe2mc.build.space", build.pretty(name).lower()))
        return None
    x0, x1, z0, z1 = rect
    tile = ((x0 + x1) / 2 / T, (z0 + z1) / 2 / T)
    owner = 0 if name in dict(tabs())["resources"] else vars(g).get("player", PLAYER)   # a mine, fish or hunt is of Gaia
    if k == "U":
        x, z = (x0 + x1) // 2, (z0 + z1) // 2
        pos = (x + 0.5, float(g.map.y(x, z)), z + 0.5)
        players = {int(p): v for p, v in g.data.get("players", {}).items()}
        nbt = units.make_entity(dict(name=name, player=owner, rotation=0.0), players, pos, np.random.default_rng())
        if nbt is None:
            return None
        kind_id = str(nbt.pop("id"))
        del nbt["Pos"]
        g.command(f"summon {kind_id} {pos[0]} {pos[1]} {pos[2]} {units.summon_snbt(nbt)}")
    else:
        r = replay.Replay(g, g.data)
        for c in r.building(name, owner, *tile, kind=k):
            g.command(c)
        g.map.blocked |= {(x, z) for x in range(x0, x1) for z in range(z0, z1)}
    g.place(export.unit_id(name), owner, tile)
    g.placed[-1]["rect"] = list(rect)                                  # for remove; export reads only id, player, tile
    if k == "U":
        g.placed[-1]["unit"] = True
    return g.placed[-1]


def rect_of(g, o):
    """(the block footprint (x0, x1, z0, z1), True for an entity only) of start object o of aoe2mc.json."""
    T = g.map.T
    if o["kind"] == "building" and "footprint" in o:
        x0, z0, x1, z1 = o["footprint"]
        return (x0, x1, z0, z1), False
    tile = int(o["tile"][0]), int(o["tile"][1])
    if o["kind"] == "other" and tile in g.map.feet:                    # a mine or a tree: its footprint
        return tuple(g.map.feet[tile]), False
    return (tile[0] * T, tile[0] * T + T, tile[1] * T, tile[1] * T + T), o["kind"] == "unit"


def remove(g, player, eye, d):
    """Remove the object at the ground that the person looks at (#6002): a placed one first (the newest), else a start
    object. Its entities go, the blocks of a building or resource go down to the ground, and its cells are free for a
    new object. Returns the footprint (x0, x1, z0, z1) or None."""
    cell = g.map.pick_ground(eye, d)
    if cell is None:
        return None
    inside = lambda r: r[0] <= cell[0] < r[1] and r[2] <= cell[1] < r[3]   # noqa: E731
    hit = next(((i, tuple(o["rect"]), o.get("unit", False)) for i, o in reversed(list(enumerate(g.placed)))
                if "rect" in o and inside(o["rect"])), None)
    if hit:
        g.placed.pop(hit[0])
    else:
        hits = [(i, *rect_of(g, o)) for i, o in enumerate(g.data["objects"]) if i not in g.removed and "tile" in o]
        hit = next((h for h in hits if inside(h[1])), None)
        if hit is None:
            return None
        g.removed.add(hit[0])
    rect, unit = hit[1], hit[2]
    x0, x1, z0, z1 = rect
    g.command(f"kill @e[type=!player,x={x0},y=-64,z={z0},dx={x1 - x0 - 1},dy=400,dz={z1 - z0 - 1}]")
    if not unit:
        ys = [y for x in range(x0, x1) for z in range(z0, z1) if (y := g.map.y(x, z)) is not None]
        if ys:
            g.command(f"fill {x0} {min(ys)} {z0} {x1 - 1} {min(ys) + HIGH} {z1 - 1} air")
        cells = {(x, z) for x in range(x0, x1) for z in range(z0, z1)}
        g.map.blocked -= cells
        for at in (g.map.farm_at, g.map.mine_at):
            for c in cells:
                at.pop(c, None)
    return rect


STEP = 100                                                             # a click on a resource: +100, shift: -100
CIV, RES, AGE = 9, 18, 27                                              # the first slot of each row of the menu
RES_ICONS = ("bread", "oak_log", "gold_ingot", "cobblestone")


def info(g, p):
    """The entry of player p in the players of aoe2mc.json (a new player: a new entry)."""
    return g.data.setdefault("players", {}).setdefault(str(p), {})


def players_menu(g, player):
    """The players menu (#6003): row 1 the current player (Gaia, 1 to 8); a click on the civilization item: the next
    civilization (shift: the one before); row 3 the resources (click +STEP, shift -STEP); row 4 the age."""
    import civs
    names = [r["name"] for r in civs.ROWS]
    p = g.player
    me = info(g, p) if p else {}
    items = [(i, "player_head" if i == p else "skeleton_skull", "Gaia" if i == 0 else f"Player {i}", "current" if i == p else "")
             for i in range(9)]
    if p:
        age = me.get("age", "dark").lower().replace("-", "_")
        items += [(CIV, "white_banner", (me.get("civ") or "-").title(), "Click: next · Shift click: before")]
        items += [(RES + k, RES_ICONS[k], f"{r.title()}: {int(me.get('resources', {}).get(r, 0))}", f"Click: +{STEP} · Shift click: -{STEP}")
                  for k, r in enumerate(export.RESOURCES)]
        items += [(AGE + k, "clock", a.name.replace("_", " ").title(), "current" if a.name == age.upper() + "_AGE" else "")
                  for k, a in enumerate(export.AGES)]

    def click(q, slot, shift, right=False):
        if slot < 9:
            g.player = slot
        elif p and slot == CIV:
            at = names.index(me["civ"]) if me.get("civ") in names else -1
            me["civ"] = names[(at + (-1 if shift else 1)) % len(names)]
        elif p and RES <= slot < RES + len(export.RESOURCES):
            res = me.setdefault("resources", {})
            r = export.RESOURCES[slot - RES]
            res[r] = max(0, int(res.get(r, 0)) + (-STEP if shift else STEP))
        elif p and AGE <= slot < AGE + len(export.AGES):
            me["age"] = export.AGES[slot - AGE].name[:-4].lower()
        players_menu(g, q)
    return menu.show(g, player, "Players", items, click)


def save(game, out, state=None):
    """Write the world and the placed objects of state into a save folder and export it to out. Returns out."""
    game.command("save-off")
    game.command("save-all flush")
    try:
        folder = savegame.write(savegame.folder(game.world), game.world, state.dump() if state else None)
        if state:                                                      # the players of the menu (#6003)
            with open(os.path.join(folder, "world", "aoe2mc.json"), "w") as f:
                json.dump(state.data, f)
    finally:
        game.command("save-on")
    path = export.export(folder, out, heights=True)
    game.command("tellraw @a " + json.dumps(lang.text("aoe2mc.editor.saved", os.path.abspath(path), color="green")))
    return path


def words(game, seen):
    """(the new log length, the count of `save` chat lines in the log after seen)."""
    log = game.server.log
    return len(log), sum(1 for line in log[seen:] if CHAT.search(line))


def tick(state):
    """One click tick: the clicks of the open menus reach their handlers."""
    return menu.clicks(state) if state.menus else []


def run(game, out, alive, state=None):
    """Answer the chat word `save` and the menu clicks while alive() (the console thread of run.main is alive)."""
    state = state or State(game)
    game.editor = state                                                # the save at the stop of run.main
    seen = len(game.server.log)
    game.command("tellraw @a " + json.dumps(lang.text("aoe2mc.editor.start", color="yellow")))   # the chat words, once
    while alive():
        tick(state)
        for line in game.server.log[seen:]:
            if m := PALETTE.search(line):
                open_menu(state, m.group(1))
            if (m := REMOVE.search(line)) and (view := state.look(m.group(1))):
                remove(state, m.group(1), *view)
            if m := PLAYERS.search(line):
                players_menu(state, m.group(1))
        seen, n = words(game, seen)
        if n:
            print(f"Saved the map: {save(game, out, state)}")
        time.sleep(0.5)
