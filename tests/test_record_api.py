"""tools/record_api.py: download writes the one .aoe2record of the zip of the record API (#4482)."""
import io
import os
import urllib.error
import zipfile

import pytest

from tools import record_api


def zipped(name, data):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr(name, data)
    return buf.getvalue()


def test_download_writes_the_record_and_returns_its_path(tmp_path):
    urls = []

    def opener(url):
        urls.append(url)
        return io.BytesIO(zipped("AgeIIDE_Replay_1.aoe2record", b"record bytes"))

    path = record_api.download("123", "456", str(tmp_path), opener=opener)
    assert path == os.path.join(str(tmp_path), "AgeIIDE_Replay_1.aoe2record")
    assert open(path, "rb").read() == b"record bytes"
    assert "gameId=123" in urls[0] and "profileId=456" in urls[0]


def test_a_missing_match_says_that_the_api_keeps_only_recent_games(tmp_path):
    def opener(url):
        raise urllib.error.HTTPError(url, 404, "Match not found.", None, None)

    with pytest.raises(SystemExit, match="only recent games"):
        record_api.download("123", "456", str(tmp_path), opener=opener)
