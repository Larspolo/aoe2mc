# Environment

The project part of the cloud environment of aoe2mc. `docs/STEERING.md` (generic) points here (#1900).

## Network

The agent starts a headless Minecraft server for tests. For this, the environment allows these hosts
(done in #12):

    piston-meta.mojang.com
    piston-data.mojang.com
    libraries.minecraft.net

The owner allowed more hosts on 2026-10-29. Test from the container on that day:

| Host | Result |
|---|---|
| `minecraft.wiki` | Works (also `?action=raw`). |
| `minecraft.net` | Redirects to `www.minecraft.net`, which the proxy blocks. |
| `aoe.ms` | Redirects to `api.ageofempires.com`, which the proxy blocks. |
| `data.aoe2companion.com`, `www.aoe2insights.com` | The proxy lets them through. The API and match pages give a Cloudflare 403. |

## Setup script

`scripts/cloud-setup.sh` installs Java 25 (the Minecraft 26.3 server, a JDK for the Paper plugin), software Vulkan
and `xdotool` (the client of `tools/mc_shot.py`), the Python packages and the Minecraft and Paper server jars.
