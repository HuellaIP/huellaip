import pytest

from colector.config import ConfigError, load_config


def test_defaults():
    cfg = load_config({})
    assert cfg.listen_port == 2055
    assert cfg.retention_days == 90
    assert cfg.min_free_bytes == 5 * 1024**3
    assert cfg.flush_seconds == 5.0
    assert cfg.goflow2_extra_args == ()


def test_overrides():
    cfg = load_config(
        {
            "LISTEN_PORT": "4739",
            "RETENTION_DAYS": "30",
            "MIN_FREE_GB": "2.5",
            "FLUSH_SECONDS": "1",
            "GOFLOW2_EXTRA_ARGS": "-loglevel debug",
        }
    )
    assert (cfg.listen_port, cfg.retention_days) == (4739, 30)
    assert cfg.min_free_bytes == int(2.5 * 1024**3)
    assert cfg.goflow2_extra_args == ("-loglevel", "debug")


@pytest.mark.parametrize(
    "key,value",
    [
        ("LISTEN_PORT", "0"),
        ("LISTEN_PORT", "70000"),
        ("RETENTION_DAYS", "0"),
        ("MIN_FREE_GB", "-1"),
        ("FLUSH_SECONDS", "abc"),
    ],
)
def test_invalid_values_raise(key, value):
    with pytest.raises(ConfigError, match=key):
        load_config({key: value})
