"""
The in-game input of a live replay (#688). The owner chose hotbar items, a chest menu for more actions and a command
for each action (#686): a right click with the clock pauses and continues, the feather sets the next speed, the ender
pearl jumps 1 minute forward, the ender eye changes to spectator mode (Paper plugin: a double tap of Shift changes
back, #910), and the chest in the last slot opens a menu with all actions (Paper plugin, game/menu.py).
`/trigger aoe_replay set N` does action N without the items, also on a vanilla server. The menu and the trigger also
jump back 1 or 5 minutes (#979): Replay.run stops, and run.py restarts the server on the saved start world. "View"
goes to the view of the next player and back to all players (#1303, Replay.fog hides the units out of its sight).

The items are carrots on a stick with the model of a clock, a feather, an ender pearl and a chest (`item_model`):
Minecraft counts a right click with a carrot on a stick (the statistic `minecraft.used`), but not with a clock.
The `custom_data` of the item in the main hand gives the action. Replay.run calls the Input with its control state.
"""
import json
import re
import time

import lang
import menu

OBJECTIVE = "aoe_replay"             # the trigger: /trigger aoe_replay set N
USE = "aoe_replay_use"                # right clicks with a carrot on a stick
SPEEDS = (0.5, 1.0, 2.0, 4.0, 8.0)
PAUSE, NEXT, JUMP, MENU, JUMP5, JUMP10, SPECTATE, BACK, BACK5, SPEED = 1, 2, 3, 4, 5, 6, 7, 8, 9, 10   # SPEED + i: SPEEDS[i]
VIEW = SPEED + len(SPEEDS)            # the view of the next player (#1303): Paper only (`aoe hide`), so not in the help
FIGHTS = VIEW + 1                     # the menu page of the large fights (#2949): Paper only, as MENU
FIGHT = FIGHTS + 1                    # FIGHT + i: fight i of the list (the next ticket jumps there)
MAX_FIGHTS = 10                       # fights in the list
PLACE = FIGHT + MAX_FIGHTS            # PLACE + i: the place of fight i only, no time jump (the chat line, #2951)
CAMERA = PLACE + MAX_FIGHTS           # the automatic camera on and off (#3369): --camera auto is the start state
FIGHT_LEAD = 10000                    # ms of game time: a fight jump goes this much before the fight start (#2950)
FIGHT_HEIGHT = 30                     # blocks above the ground of the fight place: the viewer looks down at it
JUMPS = {JUMP: 60000, JUMP5: 300000, JUMP10: 600000, BACK: -60000, BACK5: -300000}   # BACK: a jump back (#979)
ITEMS = {PAUSE: (0, "clock", "Pause / continue"), NEXT: (1, "feather", "Next speed"),
         JUMP: (2, "ender_pearl", "Jump 1 minute"), SPECTATE: (7, "ender_eye", "Spectator view"),
         MENU: (8, "chest", "Replay menu")}                                    # action: hotbar slot, model, name
PLUGIN_ONLY = (MENU, SPECTATE)        # the menu, and the way back from spectator mode (a double tap of Shift, #910)


def actions():
    """All actions: number -> name."""
    return {PAUSE: "Pause / continue", NEXT: "Next speed", JUMP: "Jump 1 minute", JUMP5: "Jump 5 minutes",
            JUMP10: "Jump 10 minutes", BACK: "Back 1 minute", BACK5: "Back 5 minutes"} | \
        {SPEED + i: f"Speed {s:g}×" for i, s in enumerate(SPEEDS)}


def item(n):
    """The hotbar item of action n."""
    _, model, name = ITEMS[n]
    return (f"minecraft:carrot_on_a_stick[item_model=\"minecraft:{model}\",item_name={json.dumps(name)},"
            f"custom_data={{{OBJECTIVE}:{n}}}]")


def help_text():
    """The chat line of the input: each action is a clickable /trigger command. Short: a RCON command has at
    most 1446 bytes (the server closes the connection): the clicks get their color from the root."""
    extra = [{"text": f"[{name}] ", "click_event": {"action": "run_command", "command": f"/trigger {OBJECTIVE} set {n}"}}
             for n, name in actions().items()]
    return json.dumps({"text": "", "color": "aqua", "extra": extra}, ensure_ascii=False, separators=(",", ":"))


def help_head():
    """The first chat line of the input (#5375): a line of its own, as the translate text makes help_text too long."""
    return json.dumps(lang.text("aoe2mc.replay_input.help", color="gray"), separators=(",", ":"))


def apply(n, control):
    """Change the control state of Replay.run for action n. Returns the text for the action bar, or None."""
    if n == PAUSE:
        control["paused"] = not control.get("paused")
        return "Paused" if control["paused"] else "Continue"
    if n == NEXT or SPEED <= n < SPEED + len(SPEEDS):
        s = control.get("speed", 1.0)
        control["speed"] = SPEEDS[n - SPEED] if n != NEXT else next((v for v in SPEEDS if v > s), SPEEDS[0])
        return f"Speed {control['speed']:g}×"
    if n in JUMPS:
        control["jump"] = max(0, control.get("time", 0) + JUMPS[n])
        m, s = divmod(int(control["jump"]) // 1000, 60)                # the time of Replay.run is a float (#803)
        return f"{'Back' if JUMPS[n] < 0 else 'Jump'} to {m:02d}:{s:02d}"
    if n == VIEW:
        views = [None, *control.get("players", {})]               # Replay.run: player -> (name, color)
        control["view"] = views[(views.index(control.get("view")) + 1) % len(views)]
        return view_name(control)
    if FIGHT <= n < FIGHT + MAX_FIGHTS and n - FIGHT < len(control.get("fights", [])):
        f = control["fights"][n - FIGHT]                           # forward or back: Replay.run restarts for back
        control["jump"], control["place"] = max(0, f["start"] - FIGHT_LEAD), list(f["tile"])
        return f"Fight at {clock_text(f['start'])}"
    if PLACE <= n < PLACE + len(control.get("fights", [])):
        control["place"] = list(control["fights"][n - PLACE]["tile"])     # the view only (#2951)
        return "Fight place"
    if n == CAMERA:                                                # Replay.run sends the shot of the camera (#3369)
        cams = [None, "auto", "player"] if control.get("views") else [None, "auto"]   # no views: no player (#4769)
        i = cams.index(control.get("camera")) if control.get("camera") in cams else -1
        control["camera"] = cams[(i + 1) % len(cams)]
        return camera_name(control)
    return None


def camera_name(control):
    """The text of the camera of the control state: "Camera: auto", "Camera: player" or "Camera: free" (#3369, #4769)."""
    return "Camera: " + (control.get("camera") or "free")


def place_commands(tile, T, ground, who="@a"):
    """The viewer above a fight place (#2950): spectator mode, FIGHT_HEIGHT blocks above the ground of the tile
    (block = tile × T), looking straight down. ground: the ground height at the tile."""
    x, z = (round(c * T + T / 2, 1) for c in tile)
    return [f"gamemode spectator {who}", f"tp {who} {x} {min(319, ground + FIGHT_HEIGHT)} {z} 0 90"]


def view_name(control):
    """The text of the view of the control state: "View: all players" or "View: Player 2 (Aztecs)"."""
    p = control.get("view")
    return "View: " + ("all players" if p is None else control["players"][p][0])


def clock_text(ms):
    m, s = divmod(int(ms) // 1000, 60)
    return f"{m:02d}:{s:02d}"


def fight_players(f, players):
    """The names of the players of a fight in their colors, "A vs B" (fight_lines, fight_news)."""
    return [x for k, p in enumerate(f["players"]) for x in ([lang.text("aoe2mc.replay_input.vs")] if k else []) +
            [{"text": players.get(p, (f"Player {p}", "white"))[0], "color": players.get(p, ("", "white"))[1]}]]


def fight_lines(fights, players):
    """The tellraw commands of the fight list at the start (#2949): one line per fight (at most MAX_FIGHTS), with the
    time, the players in their colors and the number of units; a click sets the trigger FIGHT + i. fights:
    replay.fights(); players: player -> (name, color). No fights: no lines."""
    out = [f"tellraw @a {json.dumps(lang.text('aoe2mc.replay_input.fights', bold=True))}"] if fights else []
    for i, f in enumerate(fights[:MAX_FIGHTS]):
        out.append("tellraw @a " + json.dumps(
            {"text": "", "click_event": {"action": "run_command", "command": f"/trigger {OBJECTIVE} set {FIGHT + i}"},
             "extra": [{"text": f"[{clock_text(f['start'])}] ", "color": "gold"}, *fight_players(f, players),
                       lang.text("aoe2mc.replay_input.units", f['units'], color="gray")]}, ensure_ascii=False))
    return out


def fight_news(f, i, players):
    """The chat line and the horn of a fight start (#2951): "Fight: A vs B, N units". A click sets the trigger
    PLACE + i: the viewer goes above the place, without a time jump."""
    line = {"text": "", "click_event": {"action": "run_command", "command": f"/trigger {OBJECTIVE} set {PLACE + i}"},
            "extra": [lang.text("aoe2mc.replay_input.fight"), *fight_players(f, players),
                      lang.text("aoe2mc.replay_input.fight_units", f["units"], color="gray")]}
    return ["tellraw @a " + json.dumps(line, ensure_ascii=False),
            "playsound minecraft:event.raid.horn master @a ~ ~ ~ 1 1 1"]


def fight_name(f, players):
    """The menu item name of a fight: "12:34 Player 1 (Britons) vs Player 2 (Franks)"."""
    return f"{clock_text(f['start'])} " + " vs ".join(players.get(p, (f"Player {p}",))[0] for p in f["players"])


class Input:
    """poll(control) of Replay.run: reads the right clicks, the menu clicks and the trigger of all players.
    It sends commands at most each `every` seconds; the items go again to the players who lack them each `join` s."""

    def __init__(self, game, every=0.2, join=5.0, clock=time.monotonic):
        self.game, self.every, self.join, self.clock = game, every, join, clock
        self.last, self.joined = -float("inf"), -float("inf")
        self.opened = set()                                        # players with the replay menu
        if not hasattr(game, "menus"):
            game.menus = {}                                        # player -> handler of its open menu (game/menu.py)

    def setup(self):
        for c in (f"scoreboard objectives add {OBJECTIVE} trigger", f"scoreboard objectives add {USE} "
                  "minecraft.used:minecraft.carrot_on_a_stick"):
            self.game.command(c)
        if getattr(self.game, "kind", "") == "paper":
            menu.setup(self.game)

    def give(self):
        """Players who joined since the last call get the items and the help text; all may use the trigger."""
        g = self.game
        for n, (slot, _, _) in ITEMS.items():
            if n in PLUGIN_ONLY and getattr(g, "kind", "") != "paper":
                continue                                           # they need the plugin
            g.command(f"execute as @a unless items entity @s hotbar.{slot} *[custom_data={{{OBJECTIVE}:{n}}}] "
                      f"run item replace entity @s hotbar.{slot} with {item(n)}")
        for line in (help_head(), help_text()):
            g.command(f"execute as @a unless score @s {USE} matches 0.. run tellraw @s {line}")
        g.command(f"scoreboard players add @a {USE} 0")
        g.command(f"scoreboard players enable @a {OBJECTIVE}")

    def passed(self, selector):
        return "passed" in self.game.command(f"execute if entity {selector}")

    def __call__(self, control):
        now = self.clock()
        if now - self.last < self.every:
            return
        self.last, g, self.control = now, self.game, control     # control: the menu shows the view now
        if now - self.joined >= self.join:
            self.joined = now
            self.give()
        if self.passed(f"@a[scores={{{USE}=1..}}]"):              # a right click: the item in the main hand
            for n in ITEMS:
                g.command(f"execute as @a[scores={{{USE}=1..}}] if items entity @s weapon.mainhand "
                          f"*[custom_data={{{OBJECTIVE}:{n}}}] run scoreboard players set @s {OBJECTIVE} {n}")
            g.command(f"scoreboard players set @a {USE} 0")
        menu.clicks(g)                                             # a click in the menu sets the trigger score
        if not self.passed(f"@a[scores={{{OBJECTIVE}=1..}}]"):
            return
        if self.passed(f"@a[scores={{{OBJECTIVE}={SPECTATE}}}]"):        # only the player who clicked (#910)
            g.command(f"gamemode spectator @a[scores={{{OBJECTIVE}={SPECTATE}}}]")
        for n, page in ((MENU, self.open_menu), (FIGHTS, self.open_fights)):
            if self.passed(f"@a[scores={{{OBJECTIVE}={n}}}]"):
                for player in (p.strip() for p in g.command("list").split(":", 1)[-1].split(",")):
                    if player and re.search(rf" has {n}\b", g.command(f"scoreboard players get {player} {OBJECTIVE}")):
                        page(player)
        for n in [*actions(), VIEW, CAMERA, *range(FIGHT, FIGHT + MAX_FIGHTS)]:
            if self.passed(f"@a[scores={{{OBJECTIVE}={n}}}]") and (said := apply(n, control)):
                g.command(f"title @a actionbar {json.dumps({'text': said}, ensure_ascii=False)}")
                if n == VIEW:                                      # the chat line in the color of the player
                    color = control["players"][control["view"]][1] if control.get("view") is not None else "white"
                    g.command(f"tellraw @a {json.dumps({'text': said, 'color': color}, ensure_ascii=False)}")
                    for player in sorted(self.opened & set(g.menus)):
                        self.open_menu(player)                     # its item names the new view
        g.command(f"scoreboard players set @a {OBJECTIVE} 0")
        g.command(f"scoreboard players enable @a {OBJECTIVE}")

    def open_menu(self, player):
        """The chest menu with all actions. It stays open: a click sets the trigger score of the player."""
        icons = {PAUSE: "clock", NEXT: "feather"} | {n: "ender_pearl" if JUMPS[n] > 0 else "recovery_compass"
                                                      for n in JUMPS} | {SPEED + i: "feather" for i in range(len(SPEEDS))} | \
            {VIEW: "spyglass", FIGHTS: "iron_sword", CAMERA: "ender_eye"}
        fights = getattr(self, "control", {}).get("fights")
        slots = [PAUSE, NEXT, JUMP, JUMP5, JUMP10, BACK, BACK5] + [SPEED + i for i in range(len(SPEEDS))] + [VIEW] + \
            [FIGHTS] * bool(fights)
        cells = dict(zip(slots, (0, 1, 3, 4, 5, 7, 8, 9, 10, 11, 12, 13, 15, 17))) | {CAMERA: 2}   # 2: the first free cell
        names = actions() | {VIEW: view_name(getattr(self, "control", {})), FIGHTS: "Fights",
                             CAMERA: camera_name(getattr(self, "control", {}))}

        def choose(p, slot, shift):
            n = next((a for a, c in cells.items() if c == slot), None)
            if n is not None:
                self.game.command(f"scoreboard players set {p} {OBJECTIVE} {n}")
        self.opened.add(player)
        return menu.show(self.game, player, "Replay", [(cells[n], icons[n], names[n], f"/trigger {OBJECTIVE} set {n}")
                                                        for n in [*slots, CAMERA]], choose)

    def open_fights(self, player):
        """The menu page of the large fights (#2949): one item per fight, a click sets the trigger FIGHT + i."""
        control = getattr(self, "control", {})
        fights, players = control.get("fights", [])[:MAX_FIGHTS], control.get("players", {})

        def choose(p, slot, shift):
            if slot < len(fights):
                self.game.command(f"scoreboard players set {p} {OBJECTIVE} {FIGHT + slot}")
        return menu.show(self.game, player, "Fights", [(i, "iron_sword", fight_name(f, players),
                                                        f"/trigger {OBJECTIVE} set {FIGHT + i}")
                                                       for i, f in enumerate(fights)], choose)
