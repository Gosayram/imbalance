from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class BudgetAction:
	action: str
	message: str = ''


class SessionBudgetMonitor:
	def __init__(
		self,
		warn_ratio: float = 0.70,
		critical_ratio: float = 0.85,
		emergency_ratio: float = 0.95,
	) -> None:
		self._warn = warn_ratio
		self._critical = critical_ratio
		self._emergency = emergency_ratio

	def check(self, used_tokens: int, total_tokens: int) -> BudgetAction:
		if total_tokens <= 0:
			return BudgetAction(action='ok')
		ratio = used_tokens / total_tokens

		if ratio >= self._emergency:
			return BudgetAction(
				action='emergency_flush',
				message=(
					f'Context at {ratio:.0%}. Critical facts should be saved to KB. '
					'Call get_context again after compaction to restore.'
				),
			)

		if ratio >= self._critical:
			return BudgetAction(
				action='save_critical_now',
				message=(
					f'Context at {ratio:.0%}. Call save_fact() for any decisions '
					'or findings not yet saved. Compaction is imminent.'
				),
			)

		if ratio >= self._warn:
			return BudgetAction(
				action='warn',
				message=f'Context at {ratio:.0%}. Consider save_fact() for important findings.',
			)

		return BudgetAction(action='ok')
