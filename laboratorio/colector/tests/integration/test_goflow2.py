"""Supervisor plus the real GoFlow2 binary, without Docker.

Runs when GOFLOW2_BIN points to a GoFlow2 v2.2.7 binary; skipped otherwise.
"""

import json
import os
import socket
import threading
import time
from datetime import UTC, datetime
from pathlib import Path

import pytest

from colector.config import Config
from colector.process import run
from colector.writer import HourlyWriter

from .ipfix_synth import DST, DST_MAC, NAT_SRC, SRC, SRC_MAC, build_message

GOFLOW2_BIN = os.environ.get("GOFLOW2_BIN")
MAPPING = Path(__file__).resolve().parents[2] / "mapping.yaml"

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(not GOFLOW2_BIN, reason="GOFLOW2_BIN not set"),
]


def free_udp_port():
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def test_supervisor_writes_goflow2_json_with_nat_fields(tmp_path):
    port = free_udp_port()
    cfg = Config(
        listen_port=port,
        data_dir=tmp_path / "flujos",
        heartbeat_path=tmp_path / "hb.json",
        goflow2_path=Path(GOFLOW2_BIN),
        mapping_path=MAPPING,
        goflow2_extra_args=("-addr", "127.0.0.1:0"),
    )
    writer = HourlyWriter(cfg.data_dir, lambda: datetime.now(UTC), flush_seconds=0)
    stop, results = threading.Event(), []
    t = threading.Thread(target=lambda: results.append(run(cfg, writer, stop)))
    t.start()
    try:
        line = None
        deadline = time.monotonic() + 20
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            while line is None and time.monotonic() < deadline:
                s.sendto(build_message(), ("127.0.0.1", port))
                time.sleep(0.5)
                for path in cfg.data_dir.rglob("*.jsonl"):
                    text = path.read_text().splitlines()
                    if text:
                        line = text[0]
        assert line is not None, "no flow written"
        flow = json.loads(line)
        assert flow["type"] == "IPFIX"
        assert (flow["src_addr"], flow["src_port"]) == SRC
        assert (flow["dst_addr"], flow["dst_port"]) == DST
        assert (flow["bytes"], flow["packets"], flow["proto"]) == (1234, 10, "TCP")
        assert (flow["src_mac"], flow["dst_mac"]) == (SRC_MAC, DST_MAC)
        assert (flow["post_nat_src_addr"], flow["post_napt_src_port"]) == NAT_SRC
        assert (flow["post_nat_dst_addr"], flow["post_napt_dst_port"]) == DST
        assert flow["sampler_address"] == "127.0.0.1"
    finally:
        stop.set()
        t.join(20)
    assert results == [0]
