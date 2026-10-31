"""The focus and target player facts and the precise time and player color of AI scripts: up-get-focus-fact,
up-get-target-fact, up-get-precise-time, up-get-player-color (#4973). The setup of test_per_up_players.py: the bot is
player 2 (color blue in the map data), the focus player is its foe, player 1 (the share of the bot)."""
from test_per_up_players import script


def test_the_focus_and_target_player_facts_read_the_food_of_the_foe_into_a_goal():
    s, b, ally = script()
    b.share.stock["food"] = 320
    s.act(None, ("up-get-focus-fact", "food-amount", 0, 5))
    assert s.goals[5] == 320
    s.act(None, ("up-get-target-fact", "food-amount", 0, 6))
    assert s.goals[6] == 320


def test_the_precise_time_is_the_milliseconds_since_the_goal_start():
    s, b, ally = script()
    s.goals[3] = 1000
    s.step()
    b.time = 2.25
    s.act(None, ("up-get-precise-time", 3, 4))
    assert s.goals[4] == 1250


def test_the_player_color_gives_the_color_id_and_the_name_as_text():
    s, b, ally = script()
    s.act(None, ("up-get-player-color", 2, 7))
    assert s.goals[7] == 1 and s.text == "blue"               # player 2 is blue in the map data (PLAYER_COLORS)
