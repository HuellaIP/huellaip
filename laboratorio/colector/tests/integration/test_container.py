"""The collector image end to end: build, run hardened, send IPFIX, read the flow.

Runs where a Docker daemon is available (the CI); skipped otherwise.
"""

import json
import shutil
import socket
import subprocess
import time
import uuid
from pathlib import Path

import pytest

from .ipfix_synth import DST, DST_MAC, NAT_SRC, SRC, SRC_MAC, build_message

CONTEXT = Path(__file__).resolve().parents[2]
IMAGE = "huellaip/colector:dev"


def docker_available():
    if shutil.which("docker") is None:
        return False
    return subprocess.run(["docker", "info"], capture_output=True, check=False).returncode == 0


pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(not docker_available(), reason="no Docker daemon"),
]


def docker(*args, check=True):
    return subprocess.run(["docker", *args], capture_output=True, text=True, check=check)


@pytest.fixture(scope="module")
def container():
    docker("build", "-t", IMAGE, str(CONTEXT))
    volume = f"colector-test-{uuid.uuid4().hex[:8]}"
    cid = docker(
        "run", "-d",
        "--read-only", "--tmpfs", "/tmp",
        "--cap-drop", "ALL", "--security-opt", "no-new-privileges:true",
        "-p", "127.0.0.1::2055/udp",
        "-v", f"{volume}:/datos",
        IMAGE,
    ).stdout.strip()  # fmt: skip
    try:
        port = int(docker("port", cid, "2055/udp").stdout.strip().rsplit(":", 1)[1])
        yield cid, port
    finally:
        print(docker("logs", cid, check=False).stderr[-4000:])
        docker("rm", "-f", cid, check=False)
        docker("volume", "rm", volume, check=False)


def first_line(cid):
    out = docker(
        "exec", cid, "sh", "-c", "cat /datos/flujos/*/*/*/*.jsonl 2>/dev/null", check=False
    )
    lines = out.stdout.splitlines()
    return lines[0] if lines else None


def health(cid):
    return docker("inspect", "-f", "{{.State.Health.Status}}", cid).stdout.strip()


def test_container_writes_flow_and_is_healthy(container):
    cid, port = container
    line = None
    deadline = time.monotonic() + 60
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        while line is None and time.monotonic() < deadline:
            s.sendto(build_message(), ("127.0.0.1", port))
            time.sleep(1)
            line = first_line(cid)
    assert line is not None, "no flow written in 60 s"
    flow = json.loads(line)
    assert (flow["src_addr"], flow["src_port"]) == SRC
    assert (flow["dst_addr"], flow["dst_port"]) == DST
    assert (flow["bytes"], flow["packets"]) == (1234, 10)
    assert (flow["src_mac"], flow["dst_mac"]) == (SRC_MAC, DST_MAC)
    assert (flow["post_nat_src_addr"], flow["post_napt_src_port"]) == NAT_SRC
    # Behind Docker's port publishing the exporter shows as the bridge gateway; the real
    # router address is checked in staging.
    assert flow["sampler_address"]

    deadline = time.monotonic() + 150
    while health(cid) != "healthy" and time.monotonic() < deadline:
        time.sleep(5)
    assert health(cid) == "healthy"


def test_container_runs_as_unprivileged_user(container):
    cid, _ = container
    assert docker("exec", cid, "id", "-u").stdout.strip() == "10001"
