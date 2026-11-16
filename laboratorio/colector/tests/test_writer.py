import gzip
from datetime import UTC, datetime, timedelta, timezone

import pytest

from colector.writer import HourlyWriter, compress, hour_path


class FakeClock:
    def __init__(self, now):
        self.now = now

    def __call__(self):
        return self.now

    def advance(self, seconds):
        self.now += timedelta(seconds=seconds)


def test_hour_path_layout(tmp_path):
    ts = datetime(2026, 11, 13, 22, 5, tzinfo=UTC)
    assert hour_path(tmp_path, ts) == tmp_path / "2026/11/13/2026-11-13T22.jsonl"


def test_hour_path_uses_utc(tmp_path):
    ts = datetime(2026, 11, 13, 21, 5, tzinfo=timezone(timedelta(hours=-3)))
    assert hour_path(tmp_path, ts) == tmp_path / "2026/11/14/2026-11-14T00.jsonl"


def test_hour_path_rejects_naive(tmp_path):
    with pytest.raises(ValueError):
        hour_path(tmp_path, datetime(2026, 11, 13, 22))  # noqa: DTZ001 (naive on purpose)


def test_rotation_on_tick_without_traffic(tmp_path):
    clock = FakeClock(datetime(2026, 11, 13, 22, 59, 59, tzinfo=UTC))
    w = HourlyWriter(tmp_path, clock, flush_seconds=5)
    w.write(b'{"a":1}')
    clock.advance(seconds=2)  # 23:00:01, no new lines
    w.tick()
    gz = tmp_path / "2026/11/13/2026-11-13T22.jsonl.gz"
    assert gz.exists() and gzip.decompress(gz.read_bytes()) == b'{"a":1}\n'
    assert not (tmp_path / "2026/11/13/2026-11-13T22.jsonl").exists()


def test_recover_compresses_past_hours_and_appends_current(tmp_path):
    past = tmp_path / "2026/11/13/2026-11-13T20.jsonl"
    cur = tmp_path / "2026/11/13/2026-11-13T22.jsonl"
    for p in (past, cur):
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(b'{"x":0}\n')
    w = HourlyWriter(tmp_path, FakeClock(datetime(2026, 11, 13, 22, 30, tzinfo=UTC)), 5)
    assert w.recover() == [past.with_suffix(".jsonl.gz")]
    w.write(b'{"x":1}')
    w.close()
    assert cur.read_bytes() == b'{"x":0}\n{"x":1}\n'


def test_compress_never_overwrites(tmp_path):
    src = tmp_path / "2026-11-13T22.jsonl"
    src.write_bytes(b"new\n")
    (tmp_path / "2026-11-13T22.jsonl.gz").write_bytes(gzip.compress(b"old\n"))
    out = compress(src)
    assert out.name == "2026-11-13T22.1.jsonl.gz"
    assert gzip.decompress(out.read_bytes()) == b"new\n"
    assert gzip.decompress((tmp_path / "2026-11-13T22.jsonl.gz").read_bytes()) == b"old\n"
    assert not src.exists()


def test_paused_writer_drops_and_counts(tmp_path):
    w = HourlyWriter(tmp_path, FakeClock(datetime(2026, 11, 13, 22, tzinfo=UTC)), 5)
    w.paused = True
    w.write(b'{"a":1}')
    assert w.dropped_lines == 1
    assert not any(tmp_path.rglob("*.jsonl"))


def test_flush_after_flush_seconds(tmp_path):
    clock = FakeClock(datetime(2026, 11, 13, 22, tzinfo=UTC))
    mono = [100.0]
    w = HourlyWriter(tmp_path, clock, flush_seconds=5, monotonic=lambda: mono[0])
    w.write(b'{"a":1}')
    path = tmp_path / "2026/11/13/2026-11-13T22.jsonl"
    mono[0] = 106.0
    w.tick()
    assert path.read_bytes() == b'{"a":1}\n'
