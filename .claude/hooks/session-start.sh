#!/bin/bash
# Install the Python dependencies in a Claude Code cloud session, so that tests and lint work.
set -euo pipefail

if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  exit 0
fi

cd "${CLAUDE_PROJECT_DIR:-.}"
python3 -m pip install --quiet --disable-pip-version-check --root-user-action=ignore -r requirements-dev.txt
