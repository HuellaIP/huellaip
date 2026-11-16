import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

from colector.metrics import Counters
from colector.templates import main, summarize, summarize_loss

METRICS = (Path(__file__).parent / "data" / "goflow2_metrics.txt").read_text()

SAMPLE = {
    "192.168.1.1:4096": {
        "2814749767106816": {
            "template-id": 256,
            "field-count": 3,
            "fields": [
                {"pen-provided": False, "type": 8, "length": 4, "pen": 0},
                {"pen-provided": False, "type": 80, "length": 6, "pen": 0},
                {"pen-provided": True, "type": 100, "length": 4, "pen": 14988},
            ],
        }
    }
}


def test_summarize_lists_elements_per_template():
    lines = summarize(SAMPLE)
    assert lines[0] == "192.168.1.1:4096 template 256 (domain 0): 3 fields"
    assert "  IE 80 (6 bytes) destinationMacAddress" in lines
    assert "  IE 100 (4 bytes) enterprise 14988" in lines


def test_summarize_flags_nat_and_mac_elements():
    assert summarize(SAMPLE)[-2:] == [
        "NAT elements (225-228): none",
        "MAC elements (56, 80, 81, 57): 80",
    ]


def test_summarize_without_templates():
    assert summarize({}) == ["No templates received yet."]


def test_summarize_shows_the_observation_domain():
    key = str((10 << 48) | (3 << 16) | 258)  # GoFlow2's key: version, domain, template
    data = {"192.168.1.1:2055": {key: {"template-id": 258, "fields": []}}}
    assert summarize(data)[0] == "192.168.1.1:2055 template 258 (domain 3): 0 fields"


def test_summarize_loss():
    assert summarize_loss(Counters(packets=2397, template_not_found=813)) == [
        "GoFlow2: 2397 packets received, 813 dropped for a missing template (33.9 %)"
    ]
    assert summarize_loss(None) == ["GoFlow2 metrics not available"]


def serve(routes):
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            body = routes.get(self.path)
            self.send_response(200 if body is not None else 404)
            self.end_headers()
            self.wfile.write((body or "").encode())

        def log_message(self, *args):
            pass

    server = HTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server


def test_main_prints_templates_and_loss(capsys):
    server = serve({"/templates": json.dumps(SAMPLE), "/metrics": METRICS})
    try:
        assert main(f"127.0.0.1:{server.server_port}") == 0
    finally:
        server.shutdown()
    out = capsys.readouterr().out.splitlines()
    assert out[0] == "192.168.1.1:4096 template 256 (domain 0): 3 fields"
    assert out[-1] == "GoFlow2: 2 packets received, 1 dropped for a missing template (50.0 %)"


def test_main_fails_when_goflow2_is_unreachable(capsys):
    server = serve({})
    port = server.server_port
    server.shutdown()
    server.server_close()
    assert main(f"127.0.0.1:{port}") == 1
    assert "could not read" in capsys.readouterr().err
