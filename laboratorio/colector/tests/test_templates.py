from colector.templates import summarize

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
    assert lines[0] == "192.168.1.1:4096 template 256: 3 fields"
    assert "  IE 80 (6 bytes) destinationMacAddress" in lines
    assert "  IE 100 (4 bytes) enterprise 14988" in lines


def test_summarize_flags_nat_and_mac_elements():
    assert summarize(SAMPLE)[-2:] == [
        "NAT elements (225-228): none",
        "Destination MAC element: 80",
    ]


def test_summarize_without_templates():
    assert summarize({}) == ["No templates received yet."]
