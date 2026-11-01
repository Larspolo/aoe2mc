"""Heat maps of a recorded game (epic #5454, #5455): counts of the events of each player per tile, and a PNG of them."""
import math

import numpy as np
from PIL import Image

import aoe2mc


def grid(events, owner, n, kind="walk", start=0, end=math.inf):
    """{player: int array n × n (x, y)}: one count per event of the player at its `tile`, time in [start, end) ms.
    kind "walk": the move and order events (aoe2mc.UNIT_USE); "fight": the attack orders at the tile of the target
    (replay.attack, #5456). owner: replay.owners() for events with only object IDs.
    kind "death": events is the dict of death_counts() (the live replay counts the deaths, the record has none, #5458)."""
    if kind == "death":
        out = {}
        for (p, x, y), c in events.items():
            if 0 <= x < n and 0 <= y < n:
                out.setdefault(p, np.zeros((n, n), int))[x, y] += c
        return out
    if kind not in ("walk", "fight"):
        raise ValueError(f"unknown heat map kind: {kind}")
    if kind == "fight":
        import replay  # large module: only for this kind
    out = {}
    for e in events:
        if not e.get("tile") or not start <= e.get("time", 0) < end:
            continue
        if not (replay.attack(e, owner) if kind == "fight" else e.get("kind") in aoe2mc.UNIT_USE):
            continue
        p = e.get("player") or next((owner[i] for i in e.get("objects", ()) if i in owner), None)
        x, y = (int(v) for v in e["tile"][:2])
        if p and 0 <= x < n and 0 <= y < n:
            out.setdefault(p, np.zeros((n, n), int))[x, y] += 1
    return out


def death_counts(answer):
    """{(player, x, y): deaths} of the answer of "aoe deathmarks heat T" ("Deaths: team x z n ..."): team pN -> player N;
    other teams are not players."""
    f = answer.split()[1:] if answer.startswith("Deaths:") else []
    out = {}
    for team, x, z, c in zip(*[iter(f)] * 4):
        if team[:1] == "p" and team[1:].isdigit():
            key = (int(team[1:]), int(x), int(z))
            out[key] = out.get(key, 0) + int(c)
    return out


def image(grids, colors):
    """A Pillow RGB image, one pixel per tile (x right, y down): black with no count, else the color of the player with
    the highest count, brighter by the log of the count. colors: {player: (r, g, b)}."""
    if not grids:
        return Image.new("RGB", (1, 1))
    players = sorted(grids)
    stack = np.stack([grids[p] for p in players])          # (players, n, n)
    top, best = stack.max(0), stack.argmax(0)
    rgb = np.array([colors.get(p, (255, 255, 255)) for p in players], float)[best]
    level = np.log1p(top) / math.log1p(max(int(top.max()), 1))
    px = np.where(top[..., None] > 0, rgb * (0.35 + 0.65 * level[..., None]), 0)
    return Image.fromarray(np.rint(px).astype(np.uint8).transpose(1, 0, 2), "RGB")


def colors(players):
    """{player: RGB} of the players of aoe2mc.json: their dye color (aoe2mc.PLAYER_COLORS, aoe2mc.DYE)."""
    return {int(key): aoe2mc.DYE.get(dye(p, int(key)), (255, 255, 255)) for key, p in players.items()}


def dye(info, p):
    """The dye color name of player p with its line `info` of aoe2mc.json "players"."""
    return info.get("color") if info.get("color") in aoe2mc.DYE else aoe2mc.player_color(p)


SHADES = 4                  # the 4 shades of a map color: the heat from low to high (#5457)


def item_commands(grids, dyes, tile, n, limit=1400):
    """Commands `aoe heatmap TILE N X,Y,COLOR,SHADE ...` (#5457): the Paper plugin paints a map item of them and gives it
    to the spectators. One entry per tile with a count: COLOR is the map color ID (aoe2mc.MAP_DYES) of the player with
    the highest count there, SHADE 0 (low) to 3 (high) by the log of the count. dyes: {player: map color ID}.
    Each command stays below `limit` characters (RCON); the plugin gives the item at the last one ("end")."""
    head = f"aoe heatmap {tile} {n}"
    if not grids:
        return [head + " end"]
    players = sorted(grids)
    stack = np.stack([grids[p] for p in players])
    top, best = stack.max(0), stack.argmax(0)
    shade = np.minimum((np.log1p(top) / math.log1p(max(int(top.max()), 1)) * SHADES).astype(int), SHADES - 1)
    out, line = [], head
    for x, y in zip(*np.nonzero(top)):
        part = f" {x},{y},{dyes.get(players[best[x, y]], 8)},{shade[x, y]}"
        if len(line) + len(part) + 4 > limit:
            out, line = out + [line], head
        line += part
    return out + [line + " end"]
