"""
The in-game input of a live replay (#688). The owner chose hotbar items, a chest menu for more actions and a command
for each action (#686): a right click with the clock pauses and continues, the feather sets the next speed, the ender
pearl jumps 1 minute forward, and the chest in the last slot opens a menu with all actions (Paper plugin, game/menu.py).
`/trigger aoe_replay set N` does action N without the items, also on a vanilla server.

The items are carrots on a stick with the model of a clock, a feather, an ender pearl and a chest (`item_model`):
Minecraft counts a right click with a carrot on a stick (the statistic `minecraft.used`), but not with a clock.
The `custom_data` of the item in the main hand gives the action. Replay.run calls the Input with its control state.
"""
import json
import re
import time

import menu

OBJECTIVE = "aoe_replay"             # the trigger: /trigger aoe_replay set N
USE = "aoe_replay_use"                # right clicks with a carrot on a stick
SPEEDS = (0.5, 1.0, 2.0, 4.0, 8.0)
PAUSE, NEXT, JUMP, MENU, JUMP5, JUMP10, SPEED = 1, 2, 3, 4, 5, 6, 10      # SPEED + i: SPEEDS[i]
JUMPS = {JUMP: 60000, JUMP5: 300000, JUMP10: 600000}
ITEMS = {PAUSE: (0, "clock", "Pause / continue"), NEXT: (1, "feather", "Next speed"),
         JUMP: (2, "ender_pearl", "Jump 1 minute"), MENU: (8, "chest", "Replay menu")}     # action: hotbar slot, model, name


def actions():
    """All actions: number -> name."""
    return {PAUSE: "Pause / continue", NEXT: "Next speed", JUMP: "Jump 1 minute", JUMP5: "Jump 5 minutes",
            JUMP10: "Jump 10 minutes"} | {SPEED + i: f"Speed {s:g}×" for i, s in enumerate(SPEEDS)}


def item(n):
    """The hotbar item of action n."""
    _, model, name = ITEMS[n]
    return (f"minecraft:carrot_on_a_stick[item_model=\"minecraft:{model}\",item_name={json.dumps(name)},"
            f"custom_data={{{OBJECTIVE}:{n}}}]")


def help_text():
    """The chat line of the input: each action is a clickable /trigger command. Short: a RCON command has at
    most 1446 bytes (the server closes the connection)."""
    extra = [{"text": f"[{name}] ", "color": "aqua",
              "click_event": {"action": "run_command", "command": f"/trigger {OBJECTIVE} set {n}"}}
             for n, name in actions().items()]
    return json.dumps({"text": "Replay: right click the items in your hotbar, or click: ", "color": "gray",
                       "extra": extra}, ensure_ascii=False, separators=(",", ":"))


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
        control["jump"] = control.get("time", 0) + JUMPS[n]
        m, s = divmod(int(control["jump"]) // 1000, 60)                # the time of Replay.run is a float (#803)
        return f"Jump to {m:02d}:{s:02d}"
    return None


class Input:
    """poll(control) of Replay.run: reads the right clicks, the menu clicks and the trigger of all players.
    It sends commands at most each `every` seconds; the items go again to the players who lack them each `join` s."""

    def __init__(self, game, every=0.2, join=5.0, clock=time.monotonic):
        self.game, self.every, self.join, self.clock = game, every, join, clock
        self.last, self.joined = -float("inf"), -float("inf")
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
            if n == MENU and getattr(g, "kind", "") != "paper":
                continue                                           # the menu needs the plugin
            g.command(f"execute as @a unless items entity @s hotbar.{slot} *[custom_data={{{OBJECTIVE}:{n}}}] "
                      f"run item replace entity @s hotbar.{slot} with {item(n)}")
        g.command(f"execute as @a unless score @s {USE} matches 0.. run tellraw @s {help_text()}")
        g.command(f"scoreboard players add @a {USE} 0")
        g.command(f"scoreboard players enable @a {OBJECTIVE}")

    def passed(self, selector):
        return "passed" in self.game.command(f"execute if entity {selector}")

    def __call__(self, control):
        now = self.clock()
        if now - self.last < self.every:
            return
        self.last, g = now, self.game
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
        if self.passed(f"@a[scores={{{OBJECTIVE}={MENU}}}]"):
            for player in (p.strip() for p in g.command("list").split(":", 1)[-1].split(",")):
                if player and re.search(rf" has {MENU}\b", g.command(f"scoreboard players get {player} {OBJECTIVE}")):
                    self.open_menu(player)
        for n in actions():
            if self.passed(f"@a[scores={{{OBJECTIVE}={n}}}]") and (said := apply(n, control)):
                g.command(f"title @a actionbar {json.dumps({'text': said}, ensure_ascii=False)}")
        g.command(f"scoreboard players set @a {OBJECTIVE} 0")
        g.command(f"scoreboard players enable @a {OBJECTIVE}")

    def open_menu(self, player):
        """The chest menu with all actions. It stays open: a click sets the trigger score of the player."""
        icons = {PAUSE: "clock", NEXT: "feather"} | {n: "ender_pearl" for n in JUMPS} | \
            {SPEED + i: "feather" for i in range(len(SPEEDS))}
        slots = [PAUSE, NEXT, JUMP, JUMP5, JUMP10] + [SPEED + i for i in range(len(SPEEDS))]
        cells = dict(zip(slots, (0, 1, 3, 4, 5, 9, 10, 11, 12, 13)))
        names = actions()

        def choose(p, slot, shift):
            n = next((a for a, c in cells.items() if c == slot), None)
            if n is not None:
                self.game.command(f"scoreboard players set {p} {OBJECTIVE} {n}")
        return menu.show(self.game, player, "Replay", [(cells[n], icons[n], names[n], f"/trigger {OBJECTIVE} set {n}")
                                                        for n in slots], choose)
