"""The environment a measured Claude session starts with — one definition for both runners.

A measured session must see only the skills its room installs. A child `claude -p`
inherits the parent's environment, and when the parent session syncs the account's
skills (`CLAUDE_CODE_SYNC_SKILLS`), every child loaded them too: 24 catalog skills,
among them a second `mock-interview`, sat in every routing and fixture room this
repository measured before the variable was dropped here. A routing run that fired
the synced copy was recorded as no skill; a fixture run that fired it was set aside
as harness-invalid. The parent's session id goes with it, so a child is its own
session. `CLAUDECODE` guards interactive terminal nesting; a subprocess run is safe.
"""

from __future__ import annotations

import os

DROPPED = ("CLAUDECODE", "CLAUDE_CODE_SYNC_SKILLS", "CLAUDE_CODE_SESSION_ID")


def child_env(base: dict[str, str] | None = None) -> dict[str, str]:
    """The parent's environment without the variables a measured session must not inherit."""
    source = os.environ if base is None else base
    return {k: v for k, v in source.items() if k not in DROPPED}
