# SPDX-License-Identifier: Apache-2.0
"""Heartbeat written by the supervisor and the container healthcheck that reads it.

Run as `python -m colector.health`: exits 0 when healthy, 1 otherwise.
"""

import json
import os
import sys
import time
from pathlib import Path

from colector.config import load_config

MAX_AGE_SECONDS = 120.0


def beat(path: Path, now: float, child_alive: bool, low_space: bool, dropped_lines: int) -> None:
    """Writes the heartbeat atomically (temporary file and rename)."""
    status = {
        "ts": now,
        "child_alive": child_alive,
        "low_space": low_space,
        "dropped_lines": dropped_lines,
    }
    tmp = path.with_name(f".{path.name}.tmp")
    tmp.write_text(json.dumps(status))
    os.replace(tmp, path)


def check(path: Path, now: float, max_age: float = MAX_AGE_SECONDS) -> int:
    """0 if the heartbeat is recent, GoFlow2 is alive and there is enough space; 1 otherwise."""
    try:
        status = json.loads(path.read_text())
    except (OSError, ValueError):
        return 1
    fresh = now - float(status.get("ts", 0)) < max_age
    healthy = fresh and status.get("child_alive") is True and status.get("low_space") is False
    return 0 if healthy else 1


def main() -> int:
    return check(load_config(os.environ).heartbeat_path, time.time())


if __name__ == "__main__":
    sys.exit(main())
