#!/bin/bash
# The setup script of the cloud environment: the owner pastes it into the environment settings (docs/SYSTEM.md).
# Install here what the project needs before a session starts (system packages, tools).
set -euo pipefail
SETUP_VERSION=1   # raise it with each change: the SessionStart hook compares it with /etc/{name}-setup-version
SETUP_NEEDS=""    # the commands or paths that it installs: the hook checks them with the setup script of another project

python3 -m pip install --quiet -r requirements-dev.txt || true
echo "$SETUP_VERSION" > /etc/{name}-setup-version || true
