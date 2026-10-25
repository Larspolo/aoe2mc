#!/bin/bash
# Install the Python dependencies in a Claude Code cloud session, so that tests and lint work.
set -euo pipefail

if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  exit 0
fi

cd "${CLAUDE_PROJECT_DIR:-.}"
python3 -m pip install --quiet --disable-pip-version-check --root-user-action=ignore -r requirements-dev.txt

# The environment runs the setup script that the owner pasted. Tell the agent when it is older than the repository.
want=$(sed -n 's/^SETUP_VERSION=\([0-9]*\).*/\1/p' scripts/cloud-setup.sh)
have=$(cat /etc/aoe2mc-setup-version 2>/dev/null || echo none)
if [ "$have" != "$want" ]; then
  echo "aoe2mc: the cloud environment runs setup script version $have, scripts/cloud-setup.sh is version $want." \
       "If no open ticket asks the owner to paste it, make one (needs-human, P1, size:S) with the steps" \
       "of docs/STEERING.md, section 'Setup script (faster start)'."
fi
