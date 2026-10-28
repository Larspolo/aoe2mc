"""The items of an "aoe menu" command in the tests (#2099): a test checks the item of its own unit or technology, not
the whole menu line, so two tickets that add an item to one menu do not change the same test line. One test per
building checks the order of the full menu with `order()`, made from the data (`game/data/train.jsonl`)."""
import re
from urllib.parse import unquote

from game import train

ITEM = re.compile(r" (\d+):([a-z_]+):([^:]+):(.*?)(?= \d+:[a-z_]+:[^:]+:|$)")
CANCEL = "Click: cancel 1"                                         # the text of an item of the queue row (train.show)


def items(command):
    """The items "slot:icon:label:text" of a menu command, in its order."""
    return [":".join(m) for m in ITEM.findall(unquote(command))]


def item(command, label):
    """The one item "slot:icon:label:text" with label in a menu command (not an item of the queue row), else None."""
    found = [s for s in items(command) if s.split(":")[2] == label and not s.endswith(CANCEL)]
    assert len(found) <= 1, found
    return found[0] if found else None


def labels(command):
    """The (slot, label) of each item of a menu command but the queue row, in its order."""
    return [(int(s.split(":")[0]), s.split(":")[2]) for s in items(command) if not s.endswith(CANCEL)]


def order(g, building):
    """The (slot, label) of each item of the menu of building of the player of g, from the data: the units and
    technologies of train.TRAINS that the player can order now (train.trains, repeatable, unlocked), in that order, and
    the rally point of a building that trains units."""
    return [train.slots(building, n)[::2] for n in train.trains(g, building) if train.repeatable(g, n) and train.unlocked(g, n)] \
        + [train.RALLY[::2]] * bool(train.units_of(g, building))
