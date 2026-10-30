#!/bin/bash
# Install the Python dependencies in a Claude Code cloud session, so that tests and lint work.
set -euo pipefail

# The merge driver of game/data/*.jsonl (.gitattributes, #2004): merge the lines by "name", not by union. Also local.
# A copy in the git directory: an older branch that merges main does not have framework/tools/merge_jsonl.py in its tree.
( cd "${CLAUDE_PROJECT_DIR:-.}" && gd=$(git rev-parse --path-format=absolute --git-common-dir) &&
  cp framework/tools/merge_jsonl.py "$gd/" && git config merge.jsonl.driver "python3 $gd/merge_jsonl.py %O %A %B" ) || true

# The Bash tool of a cloud session has no TMPDIR: "$TMPDIR/x.py" was "/x.py" (#2032).
if [ -n "${CLAUDE_ENV_FILE:-}" ] && [ -z "${TMPDIR:-}" ]; then
  echo "export TMPDIR=/tmp" >> "$CLAUDE_ENV_FILE"
fi

# A build of the plugin by hand (game/plugin/gradlew jar) needs JDK 25, but the cloud JAVA_HOME is JDK 21: "release
# version 25 not supported" cost 4 runs (docs/research/gameplay.md, #4331). run.build_plugin sets its own JAVA_HOME.
JDK25=/usr/lib/jvm/java-25-openjdk-amd64
if [ -n "${CLAUDE_ENV_FILE:-}" ] && [ -x "$JDK25/bin/javac" ] && [ "${JAVA_HOME:-}" != "$JDK25" ]; then
  echo "export JAVA_HOME=$JDK25" >> "$CLAUDE_ENV_FILE"
fi

# The Claude account of the run (#4236, docs/COLLABORATORS.md): the variable AGENT_ACCOUNT of the cloud environment
# of each collaborator. framework/tools/claim.py, framework/tools/report.py and framework/tools/usage.py write it into their lines.
if [ -n "${AGENT_ACCOUNT:-}" ]; then
  ( cd "${CLAUDE_PROJECT_DIR:-.}" && git config aoe2mc.account "$AGENT_ACCOUNT" ) || true
fi

if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  exit 0
fi

cd "${CLAUDE_PROJECT_DIR:-.}"
PIP="python3 -m pip install --quiet --disable-pip-version-check --root-user-action=ignore"
# As scripts/cloud-setup.sh: an older environment has the Debian pillow ("cannot import name '_imaging'") and the
# Debian setuptools, which cannot build mgz.
python3 -c "from PIL import _imaging" 2>/dev/null || $PIP --ignore-installed pillow || true
python3 -c "import mgz" 2>/dev/null || $PIP --ignore-installed setuptools || true
$PIP -r requirements-dev.txt

# The environment runs the setup script that the owner pasted. Tell the agent when it is older than the repository.
# One environment can serve more projects (#1964): it then has the version file of another project. With no version
# file of this project, tell the agent only when a need of SETUP_NEEDS (a command, a path or a path pattern) is missing.
want=$(sed -n 's/^SETUP_VERSION=\([0-9]*\).*/\1/p' scripts/cloud-setup.sh)
have=$(cat /etc/aoe2mc-setup-version 2>/dev/null || echo none)
read -ra needs <<< "$(sed -n 's/^SETUP_NEEDS="\([^"]*\)".*/\1/p' scripts/cloud-setup.sh)"
missing=""
for n in "${needs[@]}"; do
  compgen -G "$n" >/dev/null || command -v "$n" >/dev/null || missing="$missing $n"
done
if [ "$have" != "$want" ] && { [ "$have" != none ] || [ -n "$missing" ]; }; then
  echo "aoe2mc: the cloud environment runs setup script version $have, scripts/cloud-setup.sh is version $want" \
       "(missing:${missing:- none})." \
       "If no open ticket asks the owner to paste it, make one (needs-human, P1, size:S) with the steps" \
       "of framework/docs/STEERING.md, section 'Setup script (faster start)'."
fi
