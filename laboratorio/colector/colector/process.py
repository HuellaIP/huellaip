# SPDX-License-Identifier: Apache-2.0
"""Runs GoFlow2 as a child process and streams its JSON output into hourly files."""

import json
import logging
import queue
import shutil
import subprocess
import threading
import time
from datetime import UTC, datetime

from colector.config import Config
from colector.health import beat
from colector.retention import prune
from colector.writer import HourlyWriter

log = logging.getLogger("colector")

LOOP_TIMEOUT = 1.0  # the main loop wakes up at least once per second
HEALTHY_RUN_SECONDS = 60.0  # a child that lived this long resets the backoff
STOP_GRACE_SECONDS = 10.0
INVALID_LOG_EVERY = 60.0


class Backoff:
    """Exponential restart delays; exhausted after max_failures consecutive failures."""

    def __init__(self, base: float = 1.0, cap: float = 60.0, max_failures: int = 5):
        self.base = base
        self.cap = cap
        self.max_failures = max_failures
        self.failures = 0

    def next_delay(self) -> float:
        delay = min(self.cap, self.base * 2**self.failures)
        self.failures += 1
        return delay

    def reset(self) -> None:
        self.failures = 0

    @property
    def exhausted(self) -> bool:
        return self.failures >= self.max_failures


def build_goflow2_command(cfg: Config) -> list[str]:
    return [
        str(cfg.goflow2_path),
        "-listen",
        f"netflow://:{cfg.listen_port}",
        "-format",
        "json",
        "-mapping",
        str(cfg.mapping_path),
        *cfg.goflow2_extra_args,
    ]


def _free_bytes(path):
    return shutil.disk_usage(path).free


def _pump(stream, lines: queue.Queue) -> None:
    for line in iter(stream.readline, b""):
        lines.put(line)
    lines.put(None)  # end of output: the child is gone or closed stdout


def _is_json_object(line: bytes) -> bool:
    try:
        return isinstance(json.loads(line), dict)
    except ValueError:
        return False


def run(
    cfg: Config,
    writer: HourlyWriter,
    stop: threading.Event,
    popen=subprocess.Popen,
    sleep=time.sleep,
    prune_fn=prune,
    beat_fn=beat,
    prune_every: float = 60.0,
) -> int:
    """Supervises GoFlow2 until stop is set (returns 0) or it keeps crashing (returns 1)."""
    cfg.data_dir.mkdir(parents=True, exist_ok=True)
    backoff = Backoff()
    command = build_goflow2_command(cfg)
    invalid = 0
    last_invalid_log = float("-inf")

    while not stop.is_set():
        log.info("starting goflow2: %s", " ".join(command))
        started = time.monotonic()
        child = popen(command, stdout=subprocess.PIPE)
        lines: queue.Queue = queue.Queue()
        threading.Thread(target=_pump, args=(child.stdout, lines), daemon=True).start()
        last_prune = float("-inf")
        low_space = False
        alive = True

        while alive and not stop.is_set():
            try:
                line = lines.get(timeout=LOOP_TIMEOUT)
            except queue.Empty:
                line = b""
            if line is None:
                alive = False
            elif line:
                if _is_json_object(line):
                    writer.write(line)
                else:
                    invalid += 1
            writer.tick()

            now = time.monotonic()
            if invalid and now - last_invalid_log >= INVALID_LOG_EVERY:
                log.warning("dropped %d non-JSON lines from goflow2", invalid)
                invalid = 0
                last_invalid_log = now
            if now - last_prune >= prune_every:
                result = prune_fn(
                    cfg.data_dir,
                    datetime.now(UTC),
                    cfg.retention_days,
                    cfg.min_free_bytes,
                    _free_bytes,
                )
                low_space = result.low_space
                if low_space and not writer.paused:
                    log.error("free space below %d bytes: pausing writes", cfg.min_free_bytes)
                writer.paused = low_space
                beat_fn(cfg.heartbeat_path, time.time(), True, low_space, writer.dropped_lines)
                last_prune = now

        if stop.is_set():
            child.terminate()
            try:
                child.wait(STOP_GRACE_SECONDS)
            except subprocess.TimeoutExpired:
                child.kill()
                child.wait()
            while True:  # keep what goflow2 printed before it stopped
                try:
                    line = lines.get_nowait()
                except queue.Empty:
                    break
                if line and _is_json_object(line):
                    writer.write(line)
            writer.close()
            log.info("stopped")
            return 0

        code = child.wait()
        beat_fn(cfg.heartbeat_path, time.time(), False, low_space, writer.dropped_lines)
        if time.monotonic() - started >= HEALTHY_RUN_SECONDS:
            backoff.reset()
        delay = backoff.next_delay()
        if backoff.exhausted:
            log.error(
                "goflow2 exited with code %s %d times in a row: giving up", code, backoff.failures
            )
            writer.close()
            return 1
        log.warning("goflow2 exited with code %s; restarting in %.0f s", code, delay)
        sleep(delay)

    writer.close()
    return 0
