# SPDX-License-Identifier: Apache-2.0
"""Hourly JSON-lines files: one file per UTC hour, gzip-compressed when the hour closes."""

import gzip
import os
import shutil
import time
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

SUFFIX = ".jsonl"


def hour_path(root: Path, ts: datetime) -> Path:
    """Returns root/YYYY/MM/DD/YYYY-MM-DDTHH.jsonl for the UTC hour of ts."""
    if ts.tzinfo is None or ts.utcoffset() is None:
        raise ValueError("timestamp must be timezone-aware")
    t = ts.astimezone(UTC)
    return root / f"{t:%Y}" / f"{t:%m}" / f"{t:%d}" / f"{t:%Y-%m-%dT%H}{SUFFIX}"


def compress(path: Path) -> Path:
    """Compresses path to .jsonl.gz atomically and removes the original.

    Never overwrites: if the target exists (for example after the clock went back),
    the new file gets a numeric suffix (.1, .2, ...).
    """
    if not path.name.endswith(SUFFIX):
        raise ValueError(f"not a {SUFFIX} file: {path}")
    stem = path.name[: -len(SUFFIX)]
    target = path.with_name(f"{stem}{SUFFIX}.gz")
    n = 1
    while target.exists():
        target = path.with_name(f"{stem}.{n}{SUFFIX}.gz")
        n += 1
    tmp = path.with_name(f".{path.name}.gz.tmp")
    with open(path, "rb") as src, open(tmp, "wb") as raw:
        with gzip.GzipFile(filename=path.name, mode="wb", fileobj=raw) as dst:
            shutil.copyfileobj(src, dst)
        raw.flush()
        os.fsync(raw.fileno())
    os.replace(tmp, target)
    path.unlink()
    return target


class HourlyWriter:
    """Appends lines to the current hour's file and rotates when the hour changes."""

    def __init__(
        self,
        root: Path,
        clock: Callable[[], datetime],
        flush_seconds: float,
        monotonic: Callable[[], float] = time.monotonic,
    ):
        self.root = root
        self._clock = clock
        self._flush_seconds = flush_seconds
        self._monotonic = monotonic
        self._file = None
        self._path = None
        self._last_flush = monotonic()
        self.paused = False
        self.dropped_lines = 0

    def recover(self) -> list[Path]:
        """Compresses the .jsonl files of past hours left by a previous run."""
        current = hour_path(self.root, self._clock())
        return [compress(p) for p in sorted(self.root.rglob(f"*{SUFFIX}")) if p != current]

    def write(self, line: bytes) -> None:
        if self.paused:
            self.dropped_lines += 1
            return
        self._open_current()
        if not line.endswith(b"\n"):
            line += b"\n"
        self._file.write(line)

    def tick(self) -> None:
        """Rotates if the hour changed, and flushes every flush_seconds."""
        if self._path is not None and self._path != hour_path(self.root, self._clock()):
            self._rotate()
        elif self._file is not None and self._monotonic() - self._last_flush >= self._flush_seconds:
            self._file.flush()
            self._last_flush = self._monotonic()

    def close(self) -> None:
        """Flushes and closes the current file without compressing it."""
        handle, self._file, self._path = self._file, None, None
        if handle is not None:
            # close() releases the file even when the final flush fails (e.g. disk full).
            try:
                handle.flush()
            finally:
                handle.close()

    def _open_current(self) -> None:
        path = hour_path(self.root, self._clock())
        if path == self._path:
            return
        if self._file is not None:
            self._rotate()
        path.parent.mkdir(parents=True, exist_ok=True)
        # Long-lived handle: kept open across writes and closed in close().
        self._file = open(path, "ab")  # noqa: SIM115
        self._path = path

    def _rotate(self) -> None:
        old = self._path
        self.close()
        compress(old)
