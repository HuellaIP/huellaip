import json

import pytest

from colector.health import beat, check


@pytest.mark.parametrize(
    "age,alive,low,expected",
    [(10, True, False, 0), (500, True, False, 1), (10, False, False, 1), (10, True, True, 1)],
)
def test_check(tmp_path, age, alive, low, expected):
    hb = tmp_path / "hb.json"
    beat(hb, now=1000.0, child_alive=alive, low_space=low, dropped_lines=0)
    assert check(hb, now=1000.0 + age) == expected


def test_missing_heartbeat_is_unhealthy(tmp_path):
    assert check(tmp_path / "nope.json", now=0.0) == 1


def test_corrupt_heartbeat_is_unhealthy(tmp_path):
    hb = tmp_path / "hb.json"
    hb.write_text("{not json")
    assert check(hb, now=0.0) == 1


def test_beat_writes_status_and_leaves_no_temp_file(tmp_path):
    hb = tmp_path / "hb.json"
    beat(hb, now=1000.0, child_alive=True, low_space=False, dropped_lines=3)
    assert json.loads(hb.read_text())["dropped_lines"] == 3
    assert [p.name for p in tmp_path.iterdir()] == ["hb.json"]


def test_loss_alarm_is_unhealthy(tmp_path):
    hb = tmp_path / "hb.json"
    beat(hb, now=1000.0, child_alive=True, low_space=False, dropped_lines=0, loss_alarm=True)
    assert check(hb, now=1010.0) == 1


def test_beat_records_the_drop_ratio(tmp_path):
    hb = tmp_path / "hb.json"
    beat(hb, now=1000.0, child_alive=True, low_space=False, dropped_lines=0, drop_ratio=0.25)
    status = json.loads(hb.read_text())
    assert status["drop_ratio"] == 0.25 and status["loss_alarm"] is False
    assert check(hb, now=1010.0) == 0
