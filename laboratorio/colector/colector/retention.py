# SPDX-License-Identifier: Apache-2.0
"""Retention and minimum free space for the closed hourly archives."""

import re
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path

# YYYY-MM-DDTHH.jsonl.gz, or YYYY-MM-DDTHH.N.jsonl.gz when compress() avoided a collision.
_ARCHIVE = re.compile(r"^(\d{4})-(\d{2})-(\d{2})T(\d{2})(?:\.\d+)?\.jsonl\.gz$")


@dataclass(frozen=True)
class PruneResult:
    deleted: list[Path] = field(default_factory=list)
    low_space: bool = False


def _archives(root: Path) -> list[tuple[datetime, Path]]:
    found = []
    for path in root.rglob("*.jsonl.gz"):
        m = _ARCHIVE.match(path.name)
        if m:
            year, month, day, hour = (int(g) for g in m.groups())
            found.append((datetime(year, month, day, hour, tzinfo=UTC), path))
    return sorted(found)


def prune(
    root: Path,
    now: datetime,
    retention_days: int,
    min_free_bytes: int,
    free_bytes: Callable[[Path], int],
) -> PruneResult:
    """Deletes expired archives, then the oldest ones while free space is below the floor.

    Only closed archives (*.jsonl.gz) are ever deleted; the current hour's file is never touched.
    """
    deleted = []
    archives = _archives(root)
    cutoff = now - timedelta(days=retention_days)
    keep = []
    for hour, path in archives:
        if hour < cutoff:
            path.unlink()
            deleted.append(path)
        else:
            keep.append(path)
    while free_bytes(root) < min_free_bytes:
        if not keep:
            return PruneResult(deleted=deleted, low_space=True)
        oldest = keep.pop(0)
        oldest.unlink()
        deleted.append(oldest)
    return PruneResult(deleted=deleted, low_space=False)
