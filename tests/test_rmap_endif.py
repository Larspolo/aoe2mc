"""A comment in a comment of an AoE2 random map script (#4695): the inner */ does not end the outer comment, as in the
game, so a commented-out if/endif block with a comment in it stays a comment (Karsts)."""
from rmap import tokens
from test_rmap import SCRIPT, make

BLOCK = "/* old code\nif TINY_MAP\n\t#define SMALL /* a note */\nendif\n*/\n"


def test_a_commented_block_with_a_comment_in_it_gives_the_same_land():
    assert make(3, script=BLOCK + SCRIPT) == make(3)


def test_tokens_skip_nested_comments_and_keep_the_words_after_them():
    assert tokens("a /* b /* c */ d */ e /**/ f /*****/ g") == ["a", "e", "f", "g"]


def test_tokens_split_a_comment_from_a_word_at_its_side():
    assert tokens("a/* b */c {d}") == ["a", "c", "{", "d", "}"]
