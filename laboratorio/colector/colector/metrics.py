# SPDX-License-Identifier: Apache-2.0
"""Packet loss as seen by GoFlow2, read from its Prometheus endpoint.

GoFlow2 drops a whole IPFIX / NetFlow v9 packet when one of its data sets refers to a
template it has not received. Those packets show up only in its metrics, so the
supervisor reads them to report the loss instead of letting it pass silently.
"""

import re
import urllib.request
from dataclasses import dataclass

PACKETS = "goflow2_flow_traffic_packets_total"
ERRORS = "goflow2_flow_process_nf_errors_total"
_SAMPLE = re.compile(r"^(?P<name>[a-zA-Z_:][\w:]*)(?:\{(?P<labels>[^}]*)\})?\s+(?P<value>\S+)")


@dataclass(frozen=True)
class Counters:
    packets: int
    template_not_found: int


@dataclass(frozen=True)
class LossWindow:
    packets: int
    dropped: int

    @property
    def ratio(self) -> float:
        return self.dropped / self.packets if self.packets else 0.0


def parse_counters(text: str) -> Counters:
    """Sums received packets and template_not_found errors over every exporter."""
    packets = dropped = 0
    for line in text.splitlines():
        m = _SAMPLE.match(line)
        if not m:
            continue
        value = int(float(m["value"]))
        if m["name"] == PACKETS:
            packets += value
        elif m["name"] == ERRORS and 'error="template_not_found"' in (m["labels"] or ""):
            dropped += value
    return Counters(packets=packets, template_not_found=dropped)


def fetch_counters(addr: str, timeout: float = 2.0) -> Counters | None:
    """Reads GoFlow2's /metrics at host:port; None if it cannot be reached."""
    try:
        with urllib.request.urlopen(f"http://{addr}/metrics", timeout=timeout) as response:
            return parse_counters(response.read().decode())
    except (OSError, ValueError):
        return None


class LossTracker:
    """Turns cumulative counters into the loss of each interval."""

    def __init__(self):
        self._last = None

    def update(self, counters: Counters) -> LossWindow | None:
        last, self._last = self._last, counters
        if last is None:
            return None
        if counters.packets < last.packets or counters.template_not_found < last.template_not_found:
            return LossWindow(counters.packets, counters.template_not_found)  # GoFlow2 restarted
        return LossWindow(
            counters.packets - last.packets, counters.template_not_found - last.template_not_found
        )
