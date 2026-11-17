"""Supervisor plus the real GoFlow2 binary, without Docker.

Runs when GOFLOW2_BIN points to a GoFlow2 v2.2.7 binary; skipped otherwise.
"""

import json
import logging
import os
import socket
import subprocess
import threading
import time
from datetime import UTC, datetime
from pathlib import Path

import pytest

from colector.config import Config
from colector.process import build_goflow2_command, run
from colector.writer import HourlyWriter

from .ipfix_synth import (
    DST,
    DST_MAC,
    NAT_SRC,
    OUT_DST_MAC,
    OUT_SRC_MAC,
    SRC,
    SRC_MAC,
    build_message,
    build_unknown_template_message,
)

GOFLOW2_BIN = os.environ.get("GOFLOW2_BIN")
MAPPING = Path(__file__).resolve().parents[2] / "mapping.yaml"

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(not GOFLOW2_BIN, reason="GOFLOW2_BIN not set"),
]


def free_port(kind=socket.SOCK_DGRAM):
    with socket.socket(socket.AF_INET, kind) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def make_config(tmp_path, port):
    return Config(
        listen_port=port,
        data_dir=tmp_path / "flujos",
        heartbeat_path=tmp_path / "hb.json",
        goflow2_path=Path(GOFLOW2_BIN),
        mapping_path=MAPPING,
        metrics_addr=f"127.0.0.1:{free_port(socket.SOCK_STREAM)}",
    )


def first_line(cfg):
    for path in cfg.data_dir.rglob("*.jsonl"):
        lines = path.read_text().splitlines()
        if lines:
            return lines[0]
    return None


def test_supervisor_writes_goflow2_json_with_nat_fields(tmp_path):
    port = free_port()
    cfg = make_config(tmp_path, port)
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
                line = first_line(cfg)
        assert line is not None, "no flow written"
        flow = json.loads(line)
        assert flow["type"] == "IPFIX"
        assert (flow["src_addr"], flow["src_port"]) == SRC
        assert (flow["dst_addr"], flow["dst_port"]) == DST
        assert (flow["bytes"], flow["packets"], flow["proto"]) == (1234, 10, "TCP")
        # The four MAC elements are kept apart...
        assert (flow["in_src_mac"], flow["in_dst_mac"]) == (SRC_MAC, DST_MAC)
        assert (flow["out_src_mac"], flow["out_dst_mac"]) == (OUT_SRC_MAC, OUT_DST_MAC)
        # ...because GoFlow2 merges each pair into src_mac / dst_mac and the element that
        # comes later in the template wins. In the hEX order (57, 80, 81, 56) that is the
        # ingress side.
        assert (flow["src_mac"], flow["dst_mac"]) == (SRC_MAC, DST_MAC)
        assert (flow["post_nat_src_addr"], flow["post_napt_src_port"]) == NAT_SRC
        assert (flow["post_nat_dst_addr"], flow["post_napt_dst_port"]) == DST
        assert flow["sampler_address"] == "127.0.0.1"
    finally:
        stop.set()
        t.join(20)
    assert results == [0]


def test_supervisor_reports_packets_goflow2_drops(tmp_path, caplog):
    caplog.set_level(logging.WARNING)
    port = free_port()
    cfg = make_config(tmp_path, port)
    writer = HourlyWriter(cfg.data_dir, lambda: datetime.now(UTC), flush_seconds=0)
    stop, results = threading.Event(), []
    t = threading.Thread(target=lambda: results.append(run(cfg, writer, stop, prune_every=0.3)))
    t.start()
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            deadline = time.monotonic() + 20
            while first_line(cfg) is None and time.monotonic() < deadline:
                s.sendto(build_message(), ("127.0.0.1", port))
                time.sleep(0.5)
            assert first_line(cfg) is not None, "no flow written"
            time.sleep(1)  # past the warm-up interval
            alarm_seen = False
            deadline = time.monotonic() + 20
            while time.monotonic() < deadline and not alarm_seen:
                s.sendto(build_unknown_template_message(), ("127.0.0.1", port))
                time.sleep(0.2)
                status = json.loads(cfg.heartbeat_path.read_text())
                alarm_seen = status["loss_alarm"] and status["drop_ratio"] > 0
    finally:
        stop.set()
        t.join(20)
    assert results == [0]
    assert alarm_seen, "the heartbeat never raised the loss alarm"
    assert any("goflow2 dropped" in r.message for r in caplog.records)


def test_goflow2_writes_one_flow_per_line_under_concurrent_load(tmp_path):
    """GoFlow2 v2.2.7 writes each JSON object and its newline in two separate writes.
    With more than one decoding worker, two flows can end up on the same line, followed
    by an empty one, and the supervisor has to drop both. The command we build must avoid it.
    """
    port = free_port()
    cfg = make_config(tmp_path, port)
    out_path = tmp_path / "stdout.jsonl"
    with out_path.open("wb") as out:
        child = subprocess.Popen(build_goflow2_command(cfg), stdout=out)
        try:
            time.sleep(1)  # let GoFlow2 bind the port
            message = build_message()

            def blast():
                with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                    for _ in range(20000):
                        s.sendto(message, ("127.0.0.1", port))

            senders = [threading.Thread(target=blast) for _ in range(4)]
            for sender in senders:
                sender.start()
            for sender in senders:
                sender.join()
            time.sleep(3)  # let GoFlow2 drain its queue
        finally:
            child.terminate()
            child.wait(10)
    valid, invalid = 0, []
    for line in out_path.read_bytes().splitlines():
        try:
            json.loads(line)
            valid += 1
        except ValueError:
            invalid.append(line[:80])
    assert valid > 1000, "too few flows to exercise concurrent writes"
    assert invalid == [], f"{len(invalid)} lines are not one JSON object each"
