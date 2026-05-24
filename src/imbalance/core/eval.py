from __future__ import annotations

import time
from dataclasses import dataclass, field


@dataclass
class EvalQuery:
	query: str
	expected_slugs: list[str]
	scope: list[str] | None = None
	tags: list[str] | None = None
	budget_tokens: int = 2000


@dataclass
class EvalResult:
	query: str
	returned_slugs: list[str]
	expected_slugs: list[str]
	latency_ms: int
	tokens_used: int
	tokens_budget: int

	@property
	def precision_at_3(self) -> float:
		top3 = self.returned_slugs[:3]
		if not top3:
			return 0.0
		hits = sum(1 for s in top3 if s in self.expected_slugs)
		return hits / len(top3)

	@property
	def precision_at_5(self) -> float:
		top5 = self.returned_slugs[:5]
		if not top5:
			return 0.0
		hits = sum(1 for s in top5 if s in self.expected_slugs)
		return hits / len(top5)

	@property
	def recall(self) -> float:
		if not self.expected_slugs:
			return 1.0
		returned_set = set(self.returned_slugs)
		hits = sum(1 for s in self.expected_slugs if s in returned_set)
		return hits / len(self.expected_slugs)


@dataclass
class EvalReport:
	results: list[EvalResult] = field(default_factory=list)

	@property
	def avg_precision_at_3(self) -> float:
		if not self.results:
			return 0.0
		return sum(r.precision_at_3 for r in self.results) / len(self.results)

	@property
	def avg_precision_at_5(self) -> float:
		if not self.results:
			return 0.0
		return sum(r.precision_at_5 for r in self.results) / len(self.results)

	@property
	def avg_recall(self) -> float:
		if not self.results:
			return 0.0
		return sum(r.recall for r in self.results) / len(self.results)

	@property
	def avg_latency_ms(self) -> float:
		if not self.results:
			return 0.0
		return sum(r.latency_ms for r in self.results) / len(self.results)

	@property
	def avg_token_efficiency(self) -> float:
		if not self.results:
			return 0.0
		return sum(r.tokens_used / max(r.tokens_budget, 1) for r in self.results) / len(self.results)

	def format_summary(self) -> str:
		lines = [
			f'Eval Report ({len(self.results)} queries)',
			f'  P@3:    {self.avg_precision_at_3:.2f}',
			f'  P@5:    {self.avg_precision_at_5:.2f}',
			f'  Recall: {self.avg_recall:.2f}',
			f'  Latency (avg): {self.avg_latency_ms:.0f}ms',
			f'  Token efficiency: {self.avg_token_efficiency:.1%}',
		]
		return '\n'.join(lines)


async def run_eval(
	queries: list[EvalQuery],
	engine,
) -> EvalReport:
	report = EvalReport()
	for q in queries:
		start = time.monotonic()
		pack = await engine.get_context_pack(
			q.query,
			budget_tokens=q.budget_tokens,
			scope=q.scope,
			tags=q.tags,
		)
		elapsed_ms = int((time.monotonic() - start) * 1000)
		returned_slugs = [c.slug for c in pack.evidence]
		tokens_used = sum(c.token_count for c in pack.evidence)
		report.results.append(
			EvalResult(
				query=q.query,
				returned_slugs=returned_slugs,
				expected_slugs=q.expected_slugs,
				latency_ms=elapsed_ms,
				tokens_used=tokens_used,
				tokens_budget=q.budget_tokens,
			)
		)
	return report
