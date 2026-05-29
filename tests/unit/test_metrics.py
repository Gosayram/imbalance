import pytest
from imbalance.core.metrics import MetricsCollector, get_metrics, set_metrics


def test_metrics_counter():
	metrics = MetricsCollector()
	metrics.inc_counter('requests_total', method='GET')
	metrics.inc_counter('requests_total', method='GET')

	assert metrics.get_counter('requests_total', method='GET') == 2.0


def test_metrics_counter_different_labels():
	metrics = MetricsCollector()
	metrics.inc_counter('requests_total', method='GET')
	metrics.inc_counter('requests_total', method='POST')

	assert metrics.get_counter('requests_total', method='GET') == 1.0
	assert metrics.get_counter('requests_total', method='POST') == 1.0


def test_metrics_gauge():
	metrics = MetricsCollector()
	metrics.set_gauge('active_sessions', 5)
	metrics.set_gauge('active_sessions', 10)

	assert metrics.get_gauge('active_sessions') == 10.0


def test_metrics_histogram():
	metrics = MetricsCollector()
	metrics.observe_histogram('request_duration', 0.1)
	metrics.observe_histogram('request_duration', 0.2)
	metrics.observe_histogram('request_duration', 0.3)

	values = metrics.get_histogram('request_duration')
	assert len(values) == 3
	assert values == [0.1, 0.2, 0.3]


def test_metrics_render_prometheus():
	metrics = MetricsCollector()
	metrics.inc_counter('requests_total', method='GET')
	metrics.set_gauge('active_sessions', 5)

	output = metrics.render_prometheus()
	assert 'requests_total{method="GET"} 1.0' in output
	assert 'active_sessions 5' in output


def test_metrics_render_prometheus_histogram():
	metrics = MetricsCollector()
	metrics.observe_histogram('request_duration', 0.1)
	metrics.observe_histogram('request_duration', 0.5)
	metrics.observe_histogram('request_duration', 2.0)

	output = metrics.render_prometheus()
	assert 'request_duration_bucket{le="0.1"} 1' in output
	assert 'request_duration_bucket{le="0.5"} 2' in output
	assert 'request_duration_bucket{le="10.0"} 3' in output
	assert 'request_duration_bucket{le="+Inf"} 3' in output
	assert 'request_duration_count 3' in output
	assert 'request_duration_sum 2.6' in output


def test_metrics_reset():
	metrics = MetricsCollector()
	metrics.inc_counter('requests_total')
	metrics.set_gauge('active_sessions', 5)
	metrics.observe_histogram('request_duration', 0.1)

	metrics.reset()

	assert metrics.get_counter('requests_total') == 0.0
	assert metrics.get_gauge('active_sessions') == 0.0
	assert metrics.get_histogram('request_duration') == []


def test_get_metrics_singleton():
	metrics1 = get_metrics()
	metrics2 = get_metrics()
	assert metrics1 is metrics2


def test_set_metrics():
	custom = MetricsCollector()
	set_metrics(custom)
	assert get_metrics() is custom
