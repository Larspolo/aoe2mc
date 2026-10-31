#!/bin/bash
# The setup script of the cloud environment: the owner pastes it into the environment settings (framework/docs/SYSTEM.md).
# It runs before the clone: install tools by name only (system packages, runtimes), with no file of the repository.
# The SessionStart hook installs the packages of the repository (the install command of agent.toml).
set -euo pipefail
SETUP_VERSION=1   # raise it with each change: the SessionStart hook compares it with /etc/{name}-setup-version
SETUP_NEEDS=""    # the commands or paths that it installs: the hook checks them with the setup script of another project

echo "$SETUP_VERSION" > /etc/{name}-setup-version || true
