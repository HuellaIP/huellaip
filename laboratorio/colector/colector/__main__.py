# SPDX-License-Identifier: Apache-2.0
"""Entry point: python -m colector."""

import logging
import os
import signal
import sys
import threading
from datetime import UTC, datetime

from colector.config import ConfigError, load_config
from colector.process import run
from colector.writer import HourlyWriter


def main() -> int:
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", stream=sys.stderr
    )
    log = logging.getLogger("colector")
    try:
        cfg = load_config(os.environ)
    except ConfigError as err:
        log.error("invalid configuration: %s", err)
        return 2
    cfg.data_dir.mkdir(parents=True, exist_ok=True)
    writer = HourlyWriter(cfg.data_dir, lambda: datetime.now(UTC), cfg.flush_seconds)
    for path in writer.recover():
        log.info("compressed leftover file %s", path)

    stop = threading.Event()
    for sig in (signal.SIGTERM, signal.SIGINT):
        signal.signal(sig, lambda *_: stop.set())
    return run(cfg, writer, stop)


if __name__ == "__main__":
    sys.exit(main())
