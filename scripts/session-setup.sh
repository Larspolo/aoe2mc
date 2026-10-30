#!/bin/bash
# The aoe2mc-only steps of a cloud session: .claude/hooks/session-start.sh runs this file before the install command
# of agent.toml (#4801).
set -euo pipefail

# A build of the plugin by hand (game/plugin/gradlew jar) needs JDK 25, but the cloud JAVA_HOME is JDK 21: "release
# version 25 not supported" cost 4 runs (docs/research/gameplay.md, #4331). run.build_plugin sets its own JAVA_HOME.
JDK25=/usr/lib/jvm/java-25-openjdk-amd64
if [ -n "${CLAUDE_ENV_FILE:-}" ] && [ -x "$JDK25/bin/javac" ] && [ "${JAVA_HOME:-}" != "$JDK25" ]; then
  echo "export JAVA_HOME=$JDK25" >> "$CLAUDE_ENV_FILE"
fi

PIP="python3 -m pip install --quiet --disable-pip-version-check --root-user-action=ignore"
# As scripts/cloud-setup.sh: an older environment has the Debian pillow ("cannot import name '_imaging'") and the
# Debian setuptools, which cannot build mgz.
python3 -c "from PIL import _imaging" 2>/dev/null || $PIP --ignore-installed pillow || true
python3 -c "import mgz" 2>/dev/null || $PIP --ignore-installed setuptools || true
