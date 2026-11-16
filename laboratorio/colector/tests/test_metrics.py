from pathlib import Path

from colector.metrics import Counters, LossTracker, LossWindow, parse_counters

SAMPLE = (Path(__file__).parent / "data" / "goflow2_metrics.txt").read_text()


def test_parse_real_goflow2_metrics():
    # Captured from GoFlow2 v2.2.7 after one good packet and one with an unknown template.
    assert parse_counters(SAMPLE) == Counters(packets=2, template_not_found=1)


def test_parse_sums_every_exporter():
    text = (
        'goflow2_flow_traffic_packets_total{remote_ip="10.0.0.1",type="netflow"} 10\n'
        'goflow2_flow_traffic_packets_total{remote_ip="10.0.0.2",type="netflow"} 5\n'
        'goflow2_flow_process_nf_errors_total{error="template_not_found",router="10.0.0.1"} 3\n'
        'goflow2_flow_process_nf_errors_total{error="other",router="10.0.0.1"} 7\n'
    )
    assert parse_counters(text) == Counters(packets=15, template_not_found=3)


def test_parse_without_flow_metrics_gives_zeros():
    assert parse_counters("# nothing yet\n") == Counters(packets=0, template_not_found=0)


def test_tracker_first_sample_is_the_baseline():
    assert LossTracker().update(Counters(100, 10)) is None


def test_tracker_reports_the_window_between_samples():
    t = LossTracker()
    t.update(Counters(100, 10))
    assert t.update(Counters(160, 13)) == LossWindow(packets=60, dropped=3)


def test_tracker_handles_a_goflow2_restart():
    t = LossTracker()
    t.update(Counters(1000, 50))
    assert t.update(Counters(40, 2)) == LossWindow(packets=40, dropped=2)


def test_window_ratio():
    assert LossWindow(packets=200, dropped=3).ratio == 0.015
    assert LossWindow(packets=0, dropped=0).ratio == 0.0
