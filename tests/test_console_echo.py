"""The operators do not see the output of console commands in the chat (#1799)."""
from game import run


def test_console_commands_do_not_show_in_the_chat_of_an_operator():
    # AoePlugin.hit runs the "fill" of a falling building as the console, and each player is an operator (op_joined)
    props = dict(line.split("=", 1) for line in run.properties(25565, 25575, "pw").splitlines())
    assert props["broadcast-console-to-ops"] == "false"
    assert props["broadcast-rcon-to-ops"] == "false"
