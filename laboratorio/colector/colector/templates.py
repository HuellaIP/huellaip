# SPDX-License-Identifier: Apache-2.0
"""Lists the IPFIX / NetFlow v9 templates GoFlow2 has received, from its HTTP endpoint.

Inside the container: docker compose exec colector python -m colector.templates
Shows which information elements the exporter sends, never flow contents.
"""

import json
import sys
import urllib.request

TEMPLATES_URL = "http://127.0.0.1:8080/templates"

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


def summarize(data: dict) -> list[str]:
    lines, seen = [], set()
    for exporter, templates in data.items():
        for template in templates.values():
            fields = template.get("fields", [])
            lines.append(f"{exporter} template {template.get('template-id')}: {len(fields)} fields")
            for f in fields:
                ie, length = f.get("type"), f.get("length")
                if f.get("pen-provided"):
                    lines.append(f"  IE {ie} ({length} bytes) enterprise {f.get('pen')}")
                    continue
                seen.add(ie)
                lines.append(f"  IE {ie} ({length} bytes) {NAMES.get(ie, '')}".rstrip())
    if not lines:
        return ["No templates received yet."]
    nat = [str(i) for i in (225, 226, 227, 228) if i in seen]
    mac = [str(i) for i in (80, 57) if i in seen]
    lines.append(f"NAT elements (225-228): {', '.join(nat) or 'none'}")
    lines.append(f"Destination MAC element: {', '.join(mac) or 'none'}")
    return lines


def main(url: str = TEMPLATES_URL) -> int:
    try:
        with urllib.request.urlopen(url, timeout=5) as response:
            data = json.load(response)
    except (OSError, ValueError) as err:
        print(f"could not read {url}: {err}", file=sys.stderr)
        return 1
    print("\n".join(summarize(data)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
