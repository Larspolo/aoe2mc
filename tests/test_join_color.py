"""#3566: Paper 26.3 writes the name of a joining player in its own color, so the color code also stands between the
name and "joined the game". Game.op_joined must find the name: else no player gets op, a side or the spectator mode."""
from game import run


def test_a_name_in_its_own_color_counts():
    line = "[02:38:14 INFO]: System chat: \x1b[94mAlex\x1b[93m joined the game\x1b[0m"           # from a real server
    assert run.JOINED.search(line).group(1) == "Alex"


def test_the_other_join_lines_count_as_before():
    for line in ("[09:50:50 INFO]: System chat: \x1b[93mone joined the game\x1b[0m",
                 "[04:18:46] [Server thread/INFO]: Steve joined the game", "[04:18:46 INFO]: Steve joined the game"):
        assert run.JOINED.search(line)
    assert not run.JOINED.search("[02:38:14 INFO]: <Bob> System chat: \x1b[94mAlex\x1b[93m joined the game")
