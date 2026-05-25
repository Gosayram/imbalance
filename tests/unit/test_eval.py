import pytest
from imbalance.core.eval import EvalQuery, EvalResult, EvalReport


def test_eval_query_defaults():
	q = EvalQuery(query="test", expected_slugs=["a", "b"])
	assert q.scope is None
	assert q.tags is None
	assert q.budget_tokens == 2000


def test_eval_result_precision_at_3():
	result = EvalResult(
		query="test",
		returned_slugs=["a", "b", "c"],
		expected_slugs=["a", "b"],
		latency_ms=100,
		tokens_used=50,
		tokens_budget=100
	)
	assert result.precision_at_3 == pytest.approx(2/3)


def test_eval_result_precision_at_3_empty():
	result = EvalResult(
		query="test",
		returned_slugs=[],
		expected_slugs=["a"],
		latency_ms=100,
		tokens_used=50,
		tokens_budget=100
	)
	assert result.precision_at_3 == 0.0


def test_eval_result_recall():
	result = EvalResult(
		query="test",
		returned_slugs=["a", "b", "c"],
		expected_slugs=["a", "b", "d"],
		latency_ms=100,
		tokens_used=50,
		tokens_budget=100
	)
	assert result.recall == pytest.approx(2/3)


def test_eval_result_recall_empty_expected():
	result = EvalResult(
		query="test",
		returned_slugs=["a"],
		expected_slugs=[],
		latency_ms=100,
		tokens_used=50,
		tokens_budget=100
	)
	assert result.recall == 1.0


def test_eval_report_avg_precision():
	report = EvalReport()
	report.results.append(EvalResult(
		query="q1",
		returned_slugs=["a", "b", "c"],
		expected_slugs=["a", "b"],
		latency_ms=100,
		tokens_used=50,
		tokens_budget=100
	))
	report.results.append(EvalResult(
		query="q2",
		returned_slugs=["a", "b"],
		expected_slugs=["a"],
		latency_ms=50,
		tokens_used=25,
		tokens_budget=50
	))
	# avg of (2/3) and (1/2) = (0.667 + 0.5) / 2 = 0.583
	assert report.avg_precision_at_3 == pytest.approx((2/3 + 1/2) / 2)


def test_eval_report_format_summary():
	report = EvalReport()
	report.results.append(EvalResult(
		query="q1",
		returned_slugs=["a", "b"],
		expected_slugs=["a"],
		latency_ms=100,
		tokens_used=50,
		tokens_budget=100
	))
	summary = report.format_summary()
	assert "Eval Report (1 queries)" in summary
	assert "P@3:" in summary