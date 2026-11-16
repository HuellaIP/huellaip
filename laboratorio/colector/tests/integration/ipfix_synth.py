"""Builds a synthetic IPFIX (RFC 7011) message with one template and one data record.

All values are fictitious: documentation addresses (RFC 5737) and locally administered MACs.
"""

import ipaddress
import struct
import time

SRC = ("10.77.10.11", 40000)
DST = ("192.0.2.10", 443)
NAT_SRC = ("198.51.100.7", 50000)
SRC_MAC = "02:00:00:00:00:11"
DST_MAC = "02:00:00:00:00:01"
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
    (56, 6),  # sourceMacAddress
    (80, 6),  # destinationMacAddress
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
        + _mac(SRC_MAC)
        + _mac(DST_MAC)
        + _ip(NAT_SRC[0])
        + _ip(DST[0])
        + struct.pack("!HH", NAT_SRC[1], DST[1])
    )
    data_set = struct.pack("!HH", template_id, 4 + len(record)) + record

    body = template_set + data_set
    header = struct.pack("!HHIII", 10, 16 + len(body), int(time.time()), 1, observation_domain)
    return header + body
