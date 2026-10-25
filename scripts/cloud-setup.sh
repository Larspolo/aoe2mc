#!/bin/bash
# Setup script of the aoe2mc cloud environment. Paste this file into the environment settings:
# cloud environment menu in the session title bar → Edit → Setup script.
# It runs as root before Claude Code starts. The cloud keeps the result as a snapshot for about 7 days,
# so later sessions start with these tools in place. It must not fail: each step ends with `|| true`.
# It does not read the repository. The SessionStart hook installs what changed since the snapshot.
set -u

# Java 25 for the Minecraft 26.3 server (tools/mc_check.py). The image has Java 21 (for 1.21.1).
[ -x /usr/lib/jvm/java-25-openjdk-amd64/bin/java ] ||
  { apt-get update -qq && apt-get install -y -qq openjdk-25-jre-headless; } || true

# The packages of requirements-dev.txt. A pip pillow, because the Debian pillow shadows it (docs/LEARNINGS.md).
PIP="python3 -m pip install --quiet --disable-pip-version-check --root-user-action=ignore"
$PIP --ignore-installed pillow || true
$PIP "AoE2ScenarioParser>=0.9.8,<0.10" "nbtlib>=2.0.4,<3" "numpy>=1.26" "pytest>=8" "ruff>=0.6" || true

# Minecraft server jars in the cache of tools/mc_check.py (same file layout).
python3 - 1.21.1 26.3 <<'EOF' || true
import hashlib, json, os, sys, urllib.request
cache = os.path.join(os.environ.get("XDG_CACHE_HOME") or os.path.expanduser("~/.cache"), "aoe2mc", "mc")
get = lambda url: urllib.request.urlopen(url, timeout=120).read()
def save(url, path, sha1):
    if os.path.exists(path) and hashlib.sha1(open(path, "rb").read()).hexdigest() == sha1:
        return
    data = get(url)
    if hashlib.sha1(data).hexdigest() == sha1:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        open(path, "wb").write(data)
manifest = json.loads(get("https://piston-meta.mojang.com/mc/game/version_manifest_v2.json"))["versions"]
for v in (v for v in manifest if v["id"] in sys.argv[1:]):
    path = os.path.join(cache, v["id"], "version.json")
    save(v["url"], path, v["sha1"])
    server = json.load(open(path))["downloads"]["server"]
    save(server["url"], os.path.join(cache, v["id"], "server.jar"), server["sha1"])
EOF
exit 0
