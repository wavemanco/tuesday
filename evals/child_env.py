"""The environment a measured Claude session starts with — one definition for both runners.

A measured session must see only the skills its room installs. A child `claude -p`
inherits the parent's environment, and when the parent session syncs the account's
skills (`CLAUDE_CODE_SYNC_SKILLS`), every child loaded them too: 24 catalog skills,
among them a second `mock-interview`, sat in every routing and fixture room this
repository measured before the variable was dropped here. A routing run that fired
the synced copy was recorded as no skill; a fixture run that fired it was set aside
as harness-invalid. The parent's session goes with it, so a child is its own
session: in a cloud session the CLI takes its session id from
`CLAUDE_CODE_REMOTE_SESSION_ID` as well as `CLAUDE_CODE_SESSION_ID`, and with either
inherited every child run shared the parent's id and one transcript file per folder
(measured: dropping both gives each run its own id; the skill list is unchanged).
`CLAUDECODE` guards interactive terminal nesting; a subprocess run is safe.
A routing run in the personal layout (evals/README.md, "Layouts") also gets its own
config folder, `CLAUDE_CONFIG_DIR`, which holds that run's skills; every other child
keeps the parent's.
"""

from __future__ import annotations

import os

DROPPED = ("CLAUDECODE", "CLAUDE_CODE_SYNC_SKILLS", "CLAUDE_CODE_SESSION_ID", "CLAUDE_CODE_REMOTE_SESSION_ID")


def child_env(base: dict[str, str] | None = None, config_dir: str | os.PathLike | None = None) -> dict[str, str]:
    """The parent's environment without the variables a measured session must not inherit,
    with `CLAUDE_CONFIG_DIR` set to `config_dir` when one is given."""
    source = os.environ if base is None else base
    env = {k: v for k, v in source.items() if k not in DROPPED}
    if config_dir is not None:
        env["CLAUDE_CONFIG_DIR"] = str(config_dir)
    return env
