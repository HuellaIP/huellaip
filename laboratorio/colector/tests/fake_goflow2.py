"""Stand-in for GoFlow2 in the supervisor tests.

Modes: ok (prints two JSON lines and one invalid line, then waits for SIGTERM),
crash (exits with code 2 right away).
"""

import signal
import sys
import time

mode = sys.argv[1]
if mode == "crash":
    print("fake goflow2: crashing", file=sys.stderr)
    sys.exit(2)

signal.signal(signal.SIGTERM, lambda *_: sys.exit(0))
for line in ('{"type":"IPFIX","bytes":1}', '{"type":"IPFIX","bytes":2}', "not json"):
    print(line, flush=True)
while True:
    time.sleep(0.1)
