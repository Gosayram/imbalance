from __future__ import annotations

import time
from collections import defaultdict
from dataclasses import dataclass, field


@dataclass
class MetricValue:
	"""Single metric value."""
	value: float
	timestamp: float = field(default_factory=time.time)
	labels: dict[str, str] = field(default_factory=dict)


class MetricsCollector:
	"""Simple metrics collector for Prometheus-compatible metrics."""

	def __init__(self) -> None:
		self._counters: dict[str, float] = defaultdict(float)
		self._gauges: dict[str, float] = defaultdict(float)
		self._histograms: dict[str, list[float]] = defaultdict(list)
		self._labels: dict[str, dict[str, str]] = {}

	def inc_counter(self, name: str, value: float = 1.0, **labels: str) -> None:
		"""Increment counter metric."""
		key = self._make_key(name, labels)
		self._counters[key] += value
		self._labels[key] = labels

	def set_gauge(self, name: str, value: float, **labels: str) -> None:
		"""Set gauge metric."""
		key = self._make_key(name, labels)
		self._gauges[key] = value
		self._labels[key] = labels

	def observe_histogram(self, name: str, value: float, **labels: str) -> None:
		"""Observe histogram value."""
		key = self._make_key(name, labels)
		self._histograms[key].append(value)
		self._labels[key] = labels

	def get_counter(self, name: str, **labels: str) -> float:
		"""Get counter value."""
		key = self._make_key(name, labels)
		return self._counters.get(key, 0.0)

	def get_gauge(self, name: str, **labels: str) -> float:
		"""Get gauge value."""
		key = self._make_key(name, labels)
		return self._gauges.get(key, 0.0)

	def get_histogram(self, name: str, **labels: str) -> list[float]:
		"""Get histogram values."""
		key = self._make_key(name, labels)
		return self._histograms.get(key, [])

	def render_prometheus(self) -> str:
		"""Render metrics in Prometheus format."""
		lines: list[str] = []

		# Counters
		for key, value in self._counters.items():
			name = key.split('{')[0]
			labels = self._labels.get(key, {})
			labels_str = ','.join(f'{k}="{v}"' for k, v in labels.items())
			if labels_str:
				lines.append(f'{name}{{{labels_str}}} {value}')
			else:
				lines.append(f'{name} {value}')

		# Gauges
		for key, value in self._gauges.items():
			name = key.split('{')[0]
			labels = self._labels.get(key, {})
			labels_str = ','.join(f'{k}="{v}"' for k, v in labels.items())
			if labels_str:
				lines.append(f'{name}{{{labels_str}}} {value}')
			else:
				lines.append(f'{name} {value}')

		# Histograms
		for key, values in self._histograms.items():
			name = key.split('{')[0]
			labels = self._labels.get(key, {})
			labels_str = ','.join(f'{k}="{v}"' for k, v in labels.items())

			if values:
				count = len(values)
				total = sum(values)
				buckets = [0.01, 0.05, 0.1, 0.5, 1.0, 5.0, 10.0]
				for bucket in buckets:
					le_count = sum(1 for v in values if v <= bucket)
					bucket_labels = {**labels, 'le': str(bucket)}
					bucket_labels_str = ','.join(f'{k}="{v}"' for k, v in bucket_labels.items())
					lines.append(f'{name}_bucket{{{bucket_labels_str}}} {le_count}')

				# +Inf bucket
				inf_labels = {**labels, 'le': '+Inf'}
				inf_labels_str = ','.join(f'{k}="{v}"' for k, v in inf_labels.items())
				lines.append(f'{name}_bucket{{{inf_labels_str}}} {count}')

				if labels_str:
					lines.append(f'{name}_count{{{labels_str}}} {count}')
					lines.append(f'{name}_sum{{{labels_str}}} {total}')
				else:
					lines.append(f'{name}_count {count}')
					lines.append(f'{name}_sum {total}')

		return '\n'.join(lines)

	def reset(self) -> None:
		"""Reset all metrics."""
		self._counters.clear()
		self._gauges.clear()
		self._histograms.clear()
		self._labels.clear()

	def _make_key(self, name: str, labels: dict[str, str]) -> str:
		"""Make metric key from name and labels."""
		if not labels:
			return name
		labels_str = ','.join(f'{k}="{v}"' for k, v in sorted(labels.items()))
		return f'{name}{{{labels_str}}}'


# Global metrics collector
_global_metrics: MetricsCollector | None = None


def get_metrics() -> MetricsCollector:
	"""Get global metrics collector."""
	global _global_metrics
	if _global_metrics is None:
		_global_metrics = MetricsCollector()
	return _global_metrics


def set_metrics(metrics: MetricsCollector) -> None:
	"""Set global metrics collector."""
	global _global_metrics
	_global_metrics = metrics
