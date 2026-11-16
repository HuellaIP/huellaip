import pytest

from colector.config import ConfigError, load_config


def test_defaults():
    cfg = load_config({})
    assert cfg.listen_port == 2055
    assert cfg.retention_days == 90
    assert cfg.min_free_bytes == 5 * 1024**3
    assert cfg.flush_seconds == 5.0
    assert cfg.goflow2_extra_args == ()
    assert cfg.max_drop_ratio == 0.01
    assert cfg.metrics_addr == "127.0.0.1:8080"


def test_overrides():
    cfg = load_config(
        {
            "LISTEN_PORT": "4739",
            "RETENTION_DAYS": "30",
            "MIN_FREE_GB": "2.5",
            "FLUSH_SECONDS": "1",
            "GOFLOW2_EXTRA_ARGS": "-loglevel debug",
            "MAX_DROP_PERCENT": "5",
        }
    )
    assert (cfg.listen_port, cfg.retention_days) == (4739, 30)
    assert cfg.min_free_bytes == int(2.5 * 1024**3)
    assert cfg.goflow2_extra_args == ("-loglevel", "debug")
    assert cfg.max_drop_ratio == 0.05


@pytest.mark.parametrize(
    "key,value",
    [
        ("LISTEN_PORT", "0"),
        ("LISTEN_PORT", "70000"),
        ("RETENTION_DAYS", "0"),
        ("MIN_FREE_GB", "-1"),
        ("FLUSH_SECONDS", "abc"),
        ("MAX_DROP_PERCENT", "-1"),
        ("MAX_DROP_PERCENT", "101"),
    ],
)
def test_invalid_values_raise(key, value):
    with pytest.raises(ConfigError, match=key):
        load_config({key: value})
