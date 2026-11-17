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
from colector.metrics import LossTracker, fetch_counters
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
    # One decoding worker: GoFlow2 v2.2.7 writes each JSON object and its newline in two
    # separate writes, so with more workers two flows can share a line and both are lost.
    return [
        str(cfg.goflow2_path),
        "-listen",
        f"netflow://:{cfg.listen_port}?workers=1",
        "-format",
        "json",
        "-mapping",
        str(cfg.mapping_path),
        "-addr",
        cfg.metrics_addr,
        *cfg.goflow2_extra_args,
    ]


def _free_bytes(path):
    return shutil.disk_usage(path).free


def _pump(stream, lines: queue.Queue) -> None:
    for line in iter(stream.readline, b""):
        lines.put(line)
    lines.put(None)  # end of output: the child is gone or closed stdout


def _close_quietly(writer: HourlyWriter) -> None:
    try:
        writer.close()
    except OSError:
        pass  # the file is already released by close(); the buffered lines are lost


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
    metrics_fn=None,
) -> int:
    """Supervises GoFlow2 until stop is set (returns 0) or it keeps crashing (returns 1)."""
    if metrics_fn is None:
        metrics_fn = lambda: fetch_counters(cfg.metrics_addr)
    cfg.data_dir.mkdir(parents=True, exist_ok=True)
    metrics_unreachable_logged = False
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
        storage_failed = False  # a write failed since the last check
        loss = LossTracker()
        warming_up = True  # the first interval includes data sent before the templates
        loss_alarm, drop_ratio = False, 0.0
        alive = True

        while alive and not stop.is_set():
            try:
                line = lines.get(timeout=LOOP_TIMEOUT)
            except queue.Empty:
                line = b""
            if line is None:
                alive = False
            elif line and not _is_json_object(line):
                invalid += 1
                line = b""
            try:
                if line:
                    writer.write(line)
                writer.tick()
            except OSError as err:
                # Disk full or another storage error: never crash-loop the container.
                # Writes pause until the next check, and the heartbeat reports unhealthy.
                if not storage_failed:
                    log.error("cannot write flows (%s): pausing until the next check", err)
                storage_failed = True
                writer.paused = True
                _close_quietly(writer)

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
                writer.paused = low_space  # after a write error, try again
                unhealthy_storage = low_space or storage_failed

                counters = metrics_fn()
                if counters is None:
                    if not metrics_unreachable_logged:
                        log.warning("cannot read goflow2 metrics at %s", cfg.metrics_addr)
                        metrics_unreachable_logged = True
                    loss_alarm, drop_ratio = False, 0.0
                else:
                    window = loss.update(counters)
                    if window is not None:
                        drop_ratio = window.ratio
                        loss_alarm = not warming_up and drop_ratio > cfg.max_drop_ratio
                        if window.dropped:
                            level = logging.INFO if warming_up else logging.WARNING
                            why = (
                                "expected until the exporter sends its templates"
                                if warming_up
                                else "data sets whose template the exporter never sent"
                            )
                            log.log(
                                level,
                                "goflow2 dropped %d of %d packets (%.1f%%) since the last check: %s",
                                window.dropped,
                                window.packets,
                                100 * drop_ratio,
                                why,
                            )
                        warming_up = False

                beat_fn(
                    cfg.heartbeat_path,
                    time.time(),
                    True,
                    unhealthy_storage,
                    writer.dropped_lines,
                    loss_alarm=loss_alarm,
                    drop_ratio=drop_ratio,
                )
                storage_failed = False
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
