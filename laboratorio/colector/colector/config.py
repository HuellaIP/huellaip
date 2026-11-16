# SPDX-License-Identifier: Apache-2.0
"""Collector configuration, read from environment variables."""

import shlex
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

GIB = 1024**3


class ConfigError(ValueError):
    """An environment variable has an invalid value."""


@dataclass(frozen=True)
class Config:
    listen_port: int = 2055
    retention_days: int = 90
    min_free_bytes: int = 5 * GIB
    flush_seconds: float = 5.0
    goflow2_extra_args: tuple[str, ...] = ()
    data_dir: Path = Path("/datos/flujos")
    heartbeat_path: Path = Path("/tmp/colector-heartbeat.json")
    goflow2_path: Path = Path("/usr/local/bin/goflow2")
    mapping_path: Path = Path("/etc/colector/mapping.yaml")
    # Above this share of dropped packets in a check interval the container is unhealthy.
    max_drop_ratio: float = 0.01
    # GoFlow2's HTTP server (metrics and templates), reachable only inside the container.
    metrics_addr: str = "127.0.0.1:8080"


def _number(env: Mapping[str, str], key: str, kind, minimum, maximum=None):
    raw = env.get(key)
    if raw is None:
        return None
    try:
        value = kind(raw)
    except ValueError:
        raise ConfigError(f"{key} must be a number, got {raw!r}") from None
    if value < minimum or (maximum is not None and value > maximum):
        bounds = f">= {minimum}" if maximum is None else f"between {minimum} and {maximum}"
        raise ConfigError(f"{key} must be {bounds}, got {raw!r}")
    return value


def load_config(env: Mapping[str, str]) -> Config:
    """Builds a Config from environment variables, keeping the defaults for unset ones."""
    values = {}
    port = _number(env, "LISTEN_PORT", int, 1, 65535)
    if port is not None:
        values["listen_port"] = port
    days = _number(env, "RETENTION_DAYS", int, 1)
    if days is not None:
        values["retention_days"] = days
    free_gb = _number(env, "MIN_FREE_GB", float, 0)
    if free_gb is not None:
        values["min_free_bytes"] = int(free_gb * GIB)
    flush = _number(env, "FLUSH_SECONDS", float, 0.1)
    if flush is not None:
        values["flush_seconds"] = flush
    drop = _number(env, "MAX_DROP_PERCENT", float, 0, 100)
    if drop is not None:
        values["max_drop_ratio"] = drop / 100
    extra = env.get("GOFLOW2_EXTRA_ARGS")
    if extra:
        values["goflow2_extra_args"] = tuple(shlex.split(extra))
    return Config(**values)
