---
name: verify
description: Verify a change to {name} before commit. Selects the check level from the type of change. Use before each commit and when a ticket says "verify".
---

# Verify a change

## Level 1: lint and fast tests (each change)

    {lint}
    {fast}

Both must pass before the commit. Add the next levels of the project here (slow tests, a run of the program).
