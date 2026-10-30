#!/usr/bin/env python3
"""
Download the record (.aoe2record) of a recent AoE2 DE match from the record API (#4482, epic #4481).

Usage:
    python3 tools/record_api.py download GAME PROFILE DIR

The URL redirects to the match replay: the answer is a zip with one .aoe2record file. The API keeps only recent games.
"""
import argparse
import io
import os
import urllib.error
import urllib.request
import zipfile

URL = "https://aoe.ms/replay/?gameId={game}&profileId={profile}"


def download(game, profile, folder, opener=urllib.request.urlopen):
    """Write the .aoe2record of the match game of the player profile into folder and return its path."""
    try:
        with opener(URL.format(game=game, profile=profile)) as r:
            data = r.read()
    except urllib.error.HTTPError as e:
        if e.code == 404:
            raise SystemExit(f"No record of match {game}: the API keeps only recent games")
        raise
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        name = next(n for n in z.namelist() if n.endswith(".aoe2record"))
        path = os.path.join(folder, os.path.basename(name))
        with open(path, "wb") as f:
            f.write(z.read(name))
    return path


def main():
    parser = argparse.ArgumentParser(description="Download the record of a match from the AoE2 record API.")
    sub = parser.add_subparsers(dest="command", required=True)
    d = sub.add_parser("download", help="write the .aoe2record of a match into DIR and print its path")
    d.add_argument("game")
    d.add_argument("profile")
    d.add_argument("dir")
    a = parser.parse_args()
    print(download(a.game, a.profile, a.dir))


if __name__ == "__main__":
    main()
