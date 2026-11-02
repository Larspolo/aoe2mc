"""`tokens.base_parts()`: the parts of the base of each call, from the first turn of a transcript (#5615)."""
import tokens


def att(kind, text, **more):
    return {"type": "attachment", "attachment": {"type": kind, **more}, "rendered": [{"content": text}]}


def snap(**keys):
    return {"type": "attachment", "attachment": {"type": "prompt_snapshot", **keys}}


def call(base):
    return {"type": "assistant", "message": {"id": "m1", "content": [],
                                             "usage": {"input_tokens": 0, "cache_creation_input_tokens": base}}}


def records():
    return [{"type": "user", "message": {"content": "p" * 100}},
            att("instructions", "r" * 200), att("skill_listing", "s" * 100), att("date", "d" * 100),
            snap(systemPrompt=["x" * 300], cliPrefix="y" * 100),
            call(1000),
            att("instructions", "late" * 1000),                     # a later turn: not in the base of the first call
            snap(systemPrompt=["z" * 9], tools=[{"name": "Bash"}])]  # the first turn writes the tools later


def test_the_parts_share_the_base_by_their_characters():
    tools = len('{"name": "Bash"}')
    parts = tokens.base_parts(records(), 1000)
    total = 100 + 200 + 100 + 100 + 400 + tools
    assert parts["repo"] == 1000 * 200 / total
    assert parts["system"] == 1000 * 400 / total                  # the first system prompt and the CLI prefix
    assert parts["tools"] == 1000 * tools / total
    assert set(parts) == {"system", "repo", "prompt", "skills", "other", "tools"}
    assert round(sum(parts.values())) == 1000
    assert list(parts)[0] == "system"                               # the largest first


def test_an_old_transcript_has_no_parts_and_the_line_gives_the_repo_estimate():
    old = [r for r in records() if (r.get("attachment") or {}).get("type") != "prompt_snapshot"]
    assert tokens.base_parts(old, 1000) == {}
    t = tokens.analyse([call(24000)])
    assert "base 24k (repo 3k)" in tokens.line(t, repo=3000, parts={})
    line = tokens.line(t, repo=3000, parts={"tools": 9600, "system": 6300, "repo": 3000, "prompt": 1400, "mcp": 600})
    assert "base 24k (tools 9.6k, system 6.3k, repo 3.0k, prompt 1.4k) · " in line
