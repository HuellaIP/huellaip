import logging
import sys
import threading
import time
from datetime import UTC, datetime
from pathlib import Path

from colector.config import load_config
from colector.metrics import Counters
from colector.process import Backoff, build_goflow2_command, run
from colector.retention import PruneResult
from colector.writer import HourlyWriter

FAKE = Path(__file__).with_name("fake_goflow2.py")


def cfg_with_fake(tmp_path, mode):
    wrapper = tmp_path / f"goflow2-{mode}"
    wrapper.write_text(f'#!/bin/sh\nexec "{sys.executable}" "{FAKE}" {mode} "$@"\n')
    wrapper.chmod(0o755)
    cfg = load_config({})
    return type(cfg)(
        data_dir=tmp_path / "flujos",
        heartbeat_path=tmp_path / "hb.json",
        goflow2_path=wrapper,
        mapping_path=tmp_path / "mapping.yaml",
    )


def make_writer(tmp_path):
    return HourlyWriter(tmp_path / "flujos", lambda: datetime.now(UTC), flush_seconds=0)


def count_lines(tmp_path):
    return sum(p.read_bytes().count(b"\n") for p in (tmp_path / "flujos").rglob("*.jsonl"))


def wait_until(predicate, timeout=10):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return True
        time.sleep(0.05)
    return False


def run_in_thread(cfg, writer, **kwargs):
    stop, results = threading.Event(), []
    t = threading.Thread(target=lambda: results.append(run(cfg, writer, stop, **kwargs)))
    t.start()
    return stop, t, results


def test_command_uses_config():
    cfg = load_config({"LISTEN_PORT": "4739", "GOFLOW2_EXTRA_ARGS": "-loglevel debug"})
    assert build_goflow2_command(cfg) == [
        "/usr/local/bin/goflow2",
        "-listen",
        "netflow://:4739?workers=1",
        "-format",
        "json",
        "-mapping",
        "/etc/colector/mapping.yaml",
        "-addr",
        "127.0.0.1:8080",
        "-loglevel",
        "debug",
    ]


def test_backoff_exhausts_after_five_failures():
    b = Backoff(base=1, cap=60, max_failures=5)
    delays = [b.next_delay() for _ in range(5)]
    assert delays == [1, 2, 4, 8, 16] and b.exhausted


def test_backoff_caps_and_resets():
    b = Backoff(base=10, cap=30, max_failures=10)
    assert [b.next_delay() for _ in range(3)] == [10, 20, 30]
    b.reset()
    assert b.next_delay() == 10 and not b.exhausted


def test_run_writes_json_and_drops_garbage(tmp_path, caplog):
    caplog.set_level(logging.WARNING)
    writer = make_writer(tmp_path)
    stop, t, results = run_in_thread(cfg_with_fake(tmp_path, "ok"), writer, sleep=lambda _: None)
    assert wait_until(lambda: count_lines(tmp_path) == 2)
    stop.set()
    t.join(15)
    assert results == [0] and count_lines(tmp_path) == 2
    assert any("non-JSON" in r.message for r in caplog.records)


def test_run_returns_1_after_crash_loop(tmp_path):
    writer = make_writer(tmp_path)
    stop = threading.Event()
    assert run(cfg_with_fake(tmp_path, "crash"), writer, stop, sleep=lambda _: None) == 1


def test_low_space_pauses_writer(tmp_path):
    writer = make_writer(tmp_path)
    stop, t, results = run_in_thread(
        cfg_with_fake(tmp_path, "ok"),
        writer,
        sleep=lambda _: None,
        prune_fn=lambda *a, **k: PruneResult([], True),
        prune_every=0,
    )
    assert wait_until(lambda: writer.paused is True)
    stop.set()
    t.join(15)
    assert results == [0]


def test_run_writes_heartbeat(tmp_path):
    cfg = cfg_with_fake(tmp_path, "ok")
    stop, t, results = run_in_thread(cfg, make_writer(tmp_path), sleep=lambda _: None)
    assert wait_until(lambda: cfg.heartbeat_path.exists())
    stop.set()
    t.join(15)
    assert results == [0]
    assert '"child_alive": true' in cfg.heartbeat_path.read_text()


class FullDiskWriter(HourlyWriter):
    """A writer whose disk is full: every write fails like ENOSPC."""

    def write(self, line):
        raise OSError(28, "No space left on device")


def test_write_errors_pause_and_report_unhealthy_instead_of_crashing(tmp_path):
    cfg = cfg_with_fake(tmp_path, "ok")
    writer = FullDiskWriter(cfg.data_dir, lambda: datetime.now(UTC), flush_seconds=0)
    beats = []
    stop, t, results = run_in_thread(
        cfg,
        writer,
        sleep=lambda _: None,
        prune_fn=lambda *a, **k: PruneResult([], False),
        beat_fn=lambda path, now, alive, low, dropped, **k: beats.append(low),
        prune_every=0,
    )
    assert wait_until(lambda: True in beats)
    stop.set()
    t.join(15)
    assert results == [0]


def metrics_sequence(*samples):
    """metrics_fn that returns the samples in order, then keeps returning the last one."""
    it = iter(samples)
    last = [None]

    def fn():
        last[0] = next(it, last[0])
        return last[0]

    return fn


def run_collecting_beats(tmp_path, metrics_fn):
    beats = []
    stop, t, results = run_in_thread(
        cfg_with_fake(tmp_path, "ok"),
        make_writer(tmp_path),
        sleep=lambda _: None,
        prune_fn=lambda *a, **k: PruneResult([], False),
        beat_fn=lambda *a, **k: beats.append(k),
        metrics_fn=metrics_fn,
        prune_every=0,
    )
    return stop, t, results, beats


def test_drops_after_the_first_interval_raise_the_loss_alarm(tmp_path, caplog):
    caplog.set_level(logging.INFO)
    fn = metrics_sequence(Counters(0, 0), Counters(100, 0), Counters(200, 50))
    stop, t, results, beats = run_collecting_beats(tmp_path, fn)
    assert wait_until(lambda: any(b.get("loss_alarm") for b in beats))
    stop.set()
    t.join(15)
    assert results == [0]
    assert any(b.get("drop_ratio") == 0.5 for b in beats)
    assert any("dropped 50 of 100 packets" in r.message for r in caplog.records)


def test_drops_while_waiting_for_templates_do_not_alarm(tmp_path, caplog):
    caplog.set_level(logging.INFO)
    fn = metrics_sequence(Counters(0, 0), Counters(100, 40), Counters(200, 40))
    stop, t, results, beats = run_collecting_beats(tmp_path, fn)
    assert wait_until(lambda: len(beats) >= 5)
    stop.set()
    t.join(15)
    assert results == [0]
    assert not any(b.get("loss_alarm") for b in beats)
    assert any("templates" in r.message for r in caplog.records if r.levelno == logging.INFO)


def test_unreachable_metrics_do_not_alarm(tmp_path, caplog):
    caplog.set_level(logging.WARNING)
    stop, t, results, beats = run_collecting_beats(tmp_path, lambda: None)
    assert wait_until(lambda: len(beats) >= 3)
    stop.set()
    t.join(15)
    assert results == [0]
    assert not any(b.get("loss_alarm") for b in beats)
    assert sum("cannot read goflow2 metrics" in r.message for r in caplog.records) == 1
