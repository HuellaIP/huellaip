"""Builds a synthetic IPFIX (RFC 7011) message with one template and one data record.

All values are fictitious: documentation addresses (RFC 5737) and locally administered MACs.
"""

import ipaddress
import struct
import time

SRC = ("10.77.10.11", 40000)
DST = ("192.0.2.10", 443)
NAT_SRC = ("198.51.100.7", 50000)
# The four MAC elements, each with a different value: 56 and 80 on the ingress side,
# 81 and 57 on the egress side. Real routers may fill them differently (RouterOS 6.49
# repeats 80 in 57); distinct values prove each element lands in its own field.
SRC_MAC = "02:00:00:00:00:11"  # 56 sourceMacAddress
DST_MAC = "02:00:00:00:00:01"  # 80 destinationMacAddress
OUT_SRC_MAC = "02:00:00:00:00:02"  # 81 postSourceMacAddress
OUT_DST_MAC = "02:00:00:00:00:12"  # 57 postDestinationMacAddress
BYTES, PACKETS, PROTO_TCP = 1234, 10, 6

# (information element, length)
FIELDS = [
    (8, 4),  # sourceIPv4Address
    (12, 4),  # destinationIPv4Address
    (7, 2),  # sourceTransportPort
    (11, 2),  # destinationTransportPort
    (4, 1),  # protocolIdentifier
    (1, 8),  # octetDeltaCount
    (2, 8),  # packetDeltaCount
    (152, 8),  # flowStartMilliseconds
    (153, 8),  # flowEndMilliseconds
    # The MAC elements in the order RouterOS 6.49.23 sends them (template 258)
    (57, 6),  # postDestinationMacAddress
    (80, 6),  # destinationMacAddress
    (81, 6),  # postSourceMacAddress
    (56, 6),  # sourceMacAddress
    (225, 4),  # postNATSourceIPv4Address
    (226, 4),  # postNATDestinationIPv4Address
    (227, 2),  # postNAPTSourceTransportPort
    (228, 2),  # postNAPTDestinationTransportPort
]


def _ip(addr):
    return ipaddress.IPv4Address(addr).packed


def _mac(mac):
    return bytes.fromhex(mac.replace(":", ""))


def build_message(template_id: int = 256, observation_domain: int = 0) -> bytes:
    now_ms = int(time.time() * 1000)
    template = struct.pack("!HH", template_id, len(FIELDS))
    template += b"".join(struct.pack("!HH", ie, length) for ie, length in FIELDS)
    template_set = struct.pack("!HH", 2, 4 + len(template)) + template

    record = (
        _ip(SRC[0])
        + _ip(DST[0])
        + struct.pack("!HHB", SRC[1], DST[1], PROTO_TCP)
        + struct.pack("!QQQQ", BYTES, PACKETS, now_ms - 1000, now_ms)
        + _mac(OUT_DST_MAC)
        + _mac(DST_MAC)
        + _mac(OUT_SRC_MAC)
        + _mac(SRC_MAC)
        + _ip(NAT_SRC[0])
        + _ip(DST[0])
        + struct.pack("!HH", NAT_SRC[1], DST[1])
    )
    data_set = struct.pack("!HH", template_id, 4 + len(record)) + record

    body = template_set + data_set
    header = struct.pack("!HHIII", 10, 16 + len(body), int(time.time()), 1, observation_domain)
    return header + body


def build_unknown_template_message(template_id: int = 260) -> bytes:
    """A data set whose template was never announced, as RouterOS 6.49.3 sent for NAT events."""
    data_set = struct.pack("!HH", template_id, 8) + b"\x00" * 4
    return struct.pack("!HHIII", 10, 16 + len(data_set), int(time.time()), 2, 0) + data_set
