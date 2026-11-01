"""Heat maps of a recorded game (epic #5454, #5455): counts of the events of each player per tile, and a PNG of them."""
import math

import numpy as np
from PIL import Image

import aoe2mc


def grid(events, owner, n, kind="walk", start=0, end=math.inf):
    """{player: int array n × n (x, y)}: one count per event of the player at its `tile`, time in [start, end) ms.
    kind "walk": the move and order events (aoe2mc.UNIT_USE). owner: replay.owners() for events with only object IDs.
    kind "death": events is the dict of death_counts() (the live replay counts the deaths, the record has none, #5458)."""
    if kind == "death":
        out = {}
        for (p, x, y), c in events.items():
            if 0 <= x < n and 0 <= y < n:
                out.setdefault(p, np.zeros((n, n), int))[x, y] += c
        return out
    if kind != "walk":
        raise ValueError(f"unknown heat map kind: {kind}")
    out = {}
    for e in events:
        if e.get("kind") not in aoe2mc.UNIT_USE or not e.get("tile") or not start <= e.get("time", 0) < end:
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
    out = {}
    for key, p in players.items():
        dye = p.get("color") if p.get("color") in aoe2mc.DYE else aoe2mc.player_color(int(key))
        out[int(key)] = aoe2mc.DYE.get(dye, (255, 255, 255))
    return out
