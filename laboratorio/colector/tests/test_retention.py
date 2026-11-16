from datetime import UTC, datetime

from colector.retention import PruneResult, prune

PLENTY = 10**12


def make_file(root, hour, suffix):
    year, month, rest = hour.split("-", 2)
    day = rest[:2]
    path = root / year / month / day / f"{hour}{suffix}"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"x")
    return path


def make_gz(root, hour):
    return make_file(root, hour, ".jsonl.gz")


def make_jsonl(root, hour):
    return make_file(root, hour, ".jsonl")


def test_deletes_only_expired(tmp_path):
    old = make_gz(tmp_path, "2026-08-01T10")
    keep = make_gz(tmp_path, "2026-11-01T10")
    r = prune(tmp_path, datetime(2026, 11, 13, tzinfo=UTC), 90, 0, lambda _: PLENTY)
    assert r == PruneResult(deleted=[old], low_space=False)
    assert keep.exists() and not old.exists()


def test_expiry_reads_the_hour_of_suffixed_archives(tmp_path):
    old = make_file(tmp_path, "2026-08-01T10", ".1.jsonl.gz")
    r = prune(tmp_path, datetime(2026, 11, 13, tzinfo=UTC), 90, 0, lambda _: PLENTY)
    assert r.deleted == [old]


def test_frees_space_oldest_first_and_spares_current(tmp_path):
    a = make_gz(tmp_path, "2026-11-10T01")
    b = make_gz(tmp_path, "2026-11-11T01")
    cur = make_jsonl(tmp_path, "2026-11-13T22")
    r = prune(tmp_path, datetime(2026, 11, 13, 22, tzinfo=UTC), 90, 1, lambda _: 0)
    assert r.deleted == [a, b] and r.low_space is True
    assert cur.exists()


def test_stops_deleting_once_space_is_enough(tmp_path):
    a = make_gz(tmp_path, "2026-11-10T01")
    b = make_gz(tmp_path, "2026-11-11T01")
    frees = iter([0, 100])
    r = prune(tmp_path, datetime(2026, 11, 13, tzinfo=UTC), 90, 50, lambda _: next(frees))
    assert r.deleted == [a] and r.low_space is False and b.exists()


def test_ignores_unrelated_files(tmp_path):
    other = tmp_path / "notes.txt"
    other.write_text("keep me")
    tmp = make_file(tmp_path, "2026-08-01T10", ".jsonl.gz.tmp")
    r = prune(tmp_path, datetime(2026, 11, 13, tzinfo=UTC), 90, 0, lambda _: PLENTY)
    assert r.deleted == [] and other.exists() and tmp.exists()
