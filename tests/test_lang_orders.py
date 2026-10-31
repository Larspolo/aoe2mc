"""The texts of the orders of a player are `translate` components with the English fallback (#5343, item 4): a lang
file of a resource pack can give them in another language (game/lang.py, game/data/texts.jsonl)."""
import json
import re

from game import lang


def plain_json(o):
    """The English text of a parsed component or a list of components (lang.plain)."""
    if isinstance(o, list):
        return "".join(plain_json(x) for x in o)
    return lang.plain(o) if isinstance(o, dict) else str(o)


def plain_log(log):
    """The command lines of log, and after each one the English text of its JSON text components: the chat of the
    game in the words of the English table, for the checks of a text."""
    out = []
    for c in log:
        out.append(c)
        for m in re.finditer(r"[\[{]", c):
            try:
                obj, _ = json.JSONDecoder().raw_decode(c[m.start():])
            except ValueError:
                continue
            if isinstance(obj, (dict, list)):
                out.append(plain_json(obj))
    return out


class Game:
    """A game with only what the texts below read: the commands it sends."""

    def __init__(self, **attrs):
        self.log = []
        self.player = 1
        self.selected, self.soldiers, self.villagers, self.corners, self.hints = set(), {}, {}, {}, {}
        self.__dict__.update(attrs)

    def command(self, c):
        self.log.append(c)
        return ""

    def clock(self):
        return 0.0


def component(cmd):
    """The first JSON text component (object or list) of a command, parsed."""
    for m in re.finditer(r"[\[{]", cmd):
        try:
            obj, _ = json.JSONDecoder().raw_decode(cmd[m.start():])
        except ValueError:
            continue
        if isinstance(obj, (dict, list)):
            return obj
    raise AssertionError(f"no text component in {cmd}")


def first_key(obj):
    """The translate key of a component, or of the first component of a list."""
    return (obj[0] if isinstance(obj, list) else obj)["translate"]


def assert_translated(obj):
    """The text is a translate component: its key is a line of texts.jsonl, its fallback the English text of that line."""
    lead = obj[0] if isinstance(obj, list) else obj
    assert lead["translate"] in lang.EN_US
    assert lead["fallback"] == lang.EN_US[lead["translate"]]


def test_pause_says_the_pause_as_a_translate_line():
    from game import pause
    g = Game(game=None, t0=0.0, bots=[])
    pause.toggle(g, "Steve")
    assert_translated(component(g.log[-1]))


def test_follow_refuses_with_a_translate_line():
    from game import follow
    g = Game()
    follow.refuse(g, "Steve", "guard")
    assert first_key(component(g.log[-1])) == "aoe2mc.follow.refuse_guard"
    assert_translated(component(g.log[-1]))


def test_flare_chat_line_is_a_translate_line():
    from game import flare
    line = [c for c in flare.commands("Steve", 1, 2, 3, "@a") if c.startswith("tellraw")][0]
    assert_translated(component(line))


def test_build_menu_and_site_chat_are_translate_lines():
    from game import build
    menu = build.menu()
    assert len(menu) >= 2                                              # one command of RCON per text (rcon.MAX)
    assert_translated(component(menu[0]))                              # the head of the menu, then the lines
    g = Game()
    build.say(g, "Steve", lang.text("aoe2mc.build.space", "house"))
    assert_translated(component(g.log[-1]))


def test_stance_order_text_is_a_translate_line():
    from game import stance
    g = Game()
    stance.form(g, "Steve", "Box")
    assert_translated(component(g.log[-1]))


def test_garrison_back_to_work_is_a_translate_line():
    from game import garrison
    g = Game()
    garrison.all_back(g, "Steve")
    assert_translated(component(g.log[-1]))


def test_repair_stop_chat_is_a_translate_line():
    from game import repair
    g = Game(player=1)
    repair.stop(g, (0, 1, 0, 1), [], lang.text("aoe2mc.repair.no_resources", "town center", color="red"))
    assert_translated(component(g.log[-1]))


def test_hint_of_a_selection_is_a_translate_line():
    from game import hints
    g = Game(selected={"v-1"}, villagers={"v-1": 1}, ghosts={}, pointing={}, holds={}, noui=False)
    g.clock = lambda: 0.0
    hints.tick(g)
    assert_translated(component(g.log[-1]))


def test_gather_siege_mark_is_a_translate_line():
    from game import gather
    _, bar = gather.siege_mark("fort", "STABLE", 1500, "Steve")
    assert_translated(component(bar))


def test_monk_heresy_line_is_a_translate_line():
    from game import monk
    g = Game(enemies={"e-1": "KNIGHT"}, fort_names={}, garrisons={}, data={"objects": []}, sided=set(), who="@a")
    monk.die(g, "e-1")
    assert_translated(component(g.log[-1]))


def chat_of(log, prefix):
    """The English text of the component of each command of log that starts with prefix."""
    return [plain_json(component(c)) for c in log if c.startswith(prefix)]
