# SPDX-License-Identifier: Apache-2.0
"""Lists the IPFIX / NetFlow v9 templates GoFlow2 has received, and its packet loss.

Inside the container: docker compose exec colector python -m colector.templates
Shows which information elements the exporter sends, never flow contents.
"""

import json
import sys
import urllib.request

from colector.config import Config
from colector.metrics import Counters, fetch_counters

# Names only for elements verified against the IANA registry; the rest print by number.
NAMES = {
    56: "sourceMacAddress",
    57: "postDestinationMacAddress",
    80: "destinationMacAddress",
    81: "postSourceMacAddress",
    225: "postNATSourceIPv4Address",
    226: "postNATDestinationIPv4Address",
    227: "postNAPTSourceTransportPort",
    228: "postNAPTDestinationTransportPort",
}
NAT_ELEMENTS = (225, 226, 227, 228)
MAC_ELEMENTS = (56, 80, 81, 57)


def _domain(key: str) -> int | str:
    """GoFlow2 keys each template as version << 48 | observation domain << 16 | template id."""
    try:
        return (int(key) >> 16) & 0xFFFFFFFF
    except ValueError:
        return "?"


def summarize(data: dict) -> list[str]:
    lines, seen = [], set()
    for exporter, templates in data.items():
        for key, template in templates.items():
            fields = template.get("fields", [])
            lines.append(
                f"{exporter} template {template.get('template-id')} (domain {_domain(key)}): "
                f"{len(fields)} fields"
            )
            for f in fields:
                ie, length = f.get("type"), f.get("length")
                if f.get("pen-provided"):
                    lines.append(f"  IE {ie} ({length} bytes) enterprise {f.get('pen')}")
                    continue
                seen.add(ie)
                lines.append(f"  IE {ie} ({length} bytes) {NAMES.get(ie, '')}".rstrip())
    if not lines:
        return ["No templates received yet."]
    nat = [str(i) for i in NAT_ELEMENTS if i in seen]
    mac = [str(i) for i in MAC_ELEMENTS if i in seen]
    lines.append(f"NAT elements (225-228): {', '.join(nat) or 'none'}")
    lines.append(f"MAC elements (56, 80, 81, 57): {', '.join(mac) or 'none'}")
    return lines


def summarize_loss(counters: Counters | None) -> list[str]:
    """Totals since GoFlow2 started; the supervisor's log has them per interval."""
    if counters is None:
        return ["GoFlow2 metrics not available"]
    ratio = counters.template_not_found / counters.packets if counters.packets else 0.0
    line = (
        f"GoFlow2: {counters.packets} packets received, {counters.template_not_found} "
        f"dropped for a missing template ({ratio * 100:.1f} %)"
    )
    return [line]


def main(addr: str = Config().metrics_addr) -> int:
    url = f"http://{addr}/templates"
    try:
        with urllib.request.urlopen(url, timeout=5) as response:
            data = json.load(response)
    except (OSError, ValueError) as err:
        print(f"could not read {url}: {err}", file=sys.stderr)
        return 1
    print("\n".join(summarize(data) + summarize_loss(fetch_counters(addr))))
    return 0


if __name__ == "__main__":
    sys.exit(main())
